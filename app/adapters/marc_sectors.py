import logging
from collections import defaultdict
from collections.abc import Callable

import zstandard as zstd
from sqlalchemy.orm import Session

from adapters.lock_server import lock_server_client
from config import config
from entities.marc_sector import (
    SECTOR_SIZE,
    MarcRecordIndex,
    MarcSector,
    sysno_to_sector_id,
)

logger = logging.getLogger(__name__)

ZSTD_LEVEL = 7

_compressor = zstd.ZstdCompressor(level=ZSTD_LEVEL)
_decompressor = zstd.ZstdDecompressor()

CACHE_PREFIX = "marc:"


def read_marc(db: Session, base: str, system_number: str) -> bytes | None:
    """Read a single MARC record, checking Redis cache first."""
    cache_key = f"{CACHE_PREFIX}{base}:{system_number}"

    try:
        cached = lock_server_client.get(cache_key)
        if cached is not None:
            return bytes(cached)
    except Exception:
        logger.debug("Redis cache read failed for %s", cache_key)

    idx = db.get(MarcRecordIndex, (base, system_number))
    if idx is None:
        return None

    sector = db.get(MarcSector, (base, idx.sector_id))
    if sector is None:
        return None

    raw = _decompressor.decompress(sector.data)
    result = raw[idx.offset_in_sector : idx.offset_in_sector + idx.record_length]

    try:
        lock_server_client.set(cache_key, result, ex=config.marc_cache_ttl_seconds)
    except Exception:
        logger.debug("Redis cache write failed for %s", cache_key)

    return result


def _invalidate_cache(base: str, system_numbers: list[str]) -> None:
    """Delete cache entries for the given records."""
    if not system_numbers:
        return
    keys = [f"{CACHE_PREFIX}{base}:{sn}" for sn in system_numbers]
    try:
        lock_server_client.delete(*keys)
    except Exception:
        logger.debug("Redis cache invalidation failed for %d keys", len(keys))


def write_records_to_sector(
    db: Session,
    base: str,
    sector_id: int,
    records: dict[str, bytes],
) -> None:
    """Write/overwrite a full sector. `records` maps system_number -> raw MARC bytes.

    Records are sorted by sysno and concatenated before compression.
    Index rows are upserted for each record.
    """
    sorted_items = sorted(records.items(), key=lambda kv: int(kv[0]))
    blob = b"".join(marc for _, marc in sorted_items)
    compressed = _compressor.compress(blob)

    # Upsert sector blob
    sector = db.get(MarcSector, (base, sector_id))
    if sector is None:
        sector = MarcSector(
            base=base,
            sector_id=sector_id,
            data=compressed,
            record_count=len(records),
        )
        db.add(sector)
    else:
        sector.data = compressed
        sector.record_count = len(records)

    # Flush so the sector row exists before index rows reference it
    db.flush()

    # Upsert index rows
    offset = 0
    for sysno, marc_bytes in sorted_items:
        rec_len = len(marc_bytes)
        idx = db.get(MarcRecordIndex, (base, sysno))
        if idx is None:
            db.add(
                MarcRecordIndex(
                    base=base,
                    system_number=sysno,
                    sector_id=sector_id,
                    offset_in_sector=offset,
                    record_length=rec_len,
                )
            )
        else:
            idx.sector_id = sector_id
            idx.offset_in_sector = offset
            idx.record_length = rec_len
        offset += rec_len

    _invalidate_cache(base, list(records.keys()))


def upsert_record_in_sector(db: Session, base: str, system_number: str, marc_bytes: bytes) -> None:
    """Insert or replace a single record within its sector."""
    sector_id = sysno_to_sector_id(system_number)
    sector = db.get(MarcSector, (base, sector_id))

    if sector is None:
        # New sector with a single record
        write_records_to_sector(db, base, sector_id, {system_number: marc_bytes})
        return

    # Decompress existing sector, merge, rewrite
    raw = _decompressor.decompress(sector.data)
    records = _parse_blob_with_index(db, base, sector_id, raw)
    records[system_number] = marc_bytes
    write_records_to_sector(db, base, sector_id, records)


def _parse_blob_with_index(db: Session, base: str, sector_id: int, raw: bytes) -> dict[str, bytes]:
    """Reconstruct {system_number: bytes} from a decompressed blob using the index."""
    rows = db.query(MarcRecordIndex).filter_by(base=base, sector_id=sector_id).all()
    return {
        row.system_number: raw[row.offset_in_sector : row.offset_in_sector + row.record_length]
        for row in rows
    }


class SectorBuffer:
    """Accumulates records per (base, sector_id) and flushes whole sectors."""

    def __init__(self, get_db: Callable[[], Session], flush_threshold: int = SECTOR_SIZE):
        self._get_db = get_db
        self.flush_threshold = flush_threshold
        self._buffers: dict[tuple[str, int], dict[str, bytes]] = defaultdict(dict)

    @property
    def db(self) -> Session:
        return self._get_db()

    def add(self, base: str, system_number: str, marc_bytes: bytes):
        sector_id = sysno_to_sector_id(system_number)
        key = (base, sector_id)
        self._buffers[key][system_number] = marc_bytes

        if len(self._buffers[key]) >= self.flush_threshold:
            self._flush_sector(key)

    def flush_all(self):
        for key in list(self._buffers):
            self._flush_sector(key)

    def _flush_sector(self, key: tuple[str, int]):
        base, sector_id = key
        records = self._buffers.pop(key)
        if not records:
            return

        # Merge with existing sector data (if partial update)
        existing = self.db.get(MarcSector, (base, sector_id))
        if existing:
            raw = _decompressor.decompress(existing.data)
            existing_records = _parse_blob_with_index(self.db, base, sector_id, raw)
            existing_records.update(records)
            records = existing_records

        write_records_to_sector(self.db, base, sector_id, records)
