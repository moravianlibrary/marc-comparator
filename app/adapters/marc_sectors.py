import logging
from collections import defaultdict
from collections.abc import Callable

import zstandard as zstd
from marcdantic import MarcRecord
from sqlalchemy import select, tuple_
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


def marc_bytes_of(record: MarcRecord) -> bytes:
    """
    Raw MARC bytes of a record, for writing to sector storage.

    Records parsed with ``from_mrc``/``from_xml`` always carry them; ones built
    from JSON do not, and storing those would silently write nothing.
    """
    if record._marc is None:
        raise ValueError("MarcRecord carries no raw MARC bytes (not parsed from MRC or XML)")

    return record._marc


def read_marc(db: Session, base: str, system_number: str) -> bytes | None:
    """Read a single MARC record, checking Redis cache first."""
    cached = _cached_marc(base, system_number)
    if cached is not None:
        return cached

    idx = db.get(MarcRecordIndex, (base, system_number))
    if idx is None:
        return None

    sector = db.get(MarcSector, (base, idx.sector_id))
    if sector is None:
        return None

    raw = _decompressor.decompress(sector.data)
    result = raw[idx.offset_in_sector : idx.offset_in_sector + idx.record_length]

    _cache_marc(base, system_number, result)

    return result


def read_marc_many(db: Session, base: str, system_numbers: list[str]) -> dict[str, bytes]:
    """Read many records at once, decompressing each sector only once.

    Read one at a time this is two queries and a decompression per record, and
    several records of a batch usually live in the same sector — the catalogue
    sync measured 6.45 ms per record for a lookup whose only purpose is to see
    whether the record changed. Records missing from storage are simply absent
    from the result, exactly as ``read_marc`` returns None for them.
    """

    found: dict[str, bytes] = {}
    wanted = list(dict.fromkeys(system_numbers))
    if not wanted:
        return found

    missing: list[str] = []
    for system_number in wanted:
        cached = _cached_marc(base, system_number)
        if cached is None:
            missing.append(system_number)
        else:
            found[system_number] = cached
    if not missing:
        return found

    index_rows = (
        db.execute(
            select(MarcRecordIndex).where(
                tuple_(MarcRecordIndex.base, MarcRecordIndex.system_number).in_(
                    [(base, system_number) for system_number in missing]
                )
            )
        )
        .scalars()
        .all()
    )
    if not index_rows:
        return found

    by_sector: defaultdict[int, list[MarcRecordIndex]] = defaultdict(list)
    for index in index_rows:
        by_sector[index.sector_id].append(index)

    sectors = (
        db.execute(
            select(MarcSector).where(
                MarcSector.base == base, MarcSector.sector_id.in_(sorted(by_sector))
            )
        )
        .scalars()
        .all()
    )
    for sector in sectors:
        raw = _decompressor.decompress(sector.data)
        for index in by_sector[sector.sector_id]:
            record = raw[index.offset_in_sector : index.offset_in_sector + index.record_length]
            found[index.system_number] = record
            _cache_marc(base, index.system_number, record)

    return found


def _cached_marc(base: str, system_number: str) -> bytes | None:
    try:
        cached = lock_server_client.get(f"{CACHE_PREFIX}{base}:{system_number}")
    except Exception:
        logger.debug("Redis cache read failed for %s:%s", base, system_number)
        return None
    if isinstance(cached, bytes):
        return cached
    if isinstance(cached, str):
        # Only reachable if the Redis client is ever built with decode_responses.
        return cached.encode()
    return None


def _cache_marc(base: str, system_number: str, record: bytes) -> None:
    try:
        lock_server_client.set(
            f"{CACHE_PREFIX}{base}:{system_number}", record, ex=config.marc_cache_ttl_seconds
        )
    except Exception:
        logger.debug("Redis cache write failed for %s:%s", base, system_number)


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

    # One query for every index row this sector touches. Fetched one at a time
    # this was a SELECT per record — up to SECTOR_SIZE of them per write, and
    # 15% of everything the worker did.
    existing_indexes = {
        index.system_number: index
        for index in db.execute(
            select(MarcRecordIndex).where(
                MarcRecordIndex.base == base,
                MarcRecordIndex.system_number.in_([sysno for sysno, _ in sorted_items]),
            )
        )
        .scalars()
        .all()
    }

    # Upsert index rows
    offset = 0
    for sysno, marc_bytes in sorted_items:
        rec_len = len(marc_bytes)
        idx = existing_indexes.get(sysno)
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
    if records.get(system_number) == marc_bytes:
        # Already in storage byte for byte. Rewriting would recompress the whole
        # sector and evict every record sharing it from the cache, for nothing.
        return
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

    def holds(self, base: str, system_number: str) -> bool:
        """Whether this record is waiting here rather than being in storage.

        A buffered record is not readable through read_marc, and an updated one
        still reads as its previous self until the sector is written. A caller
        about to read one back has to flush first, and this is how it knows.
        """

        return system_number in self._buffers.get((base, sysno_to_sector_id(system_number)), {})

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
            if all(existing_records.get(sysno) == marc for sysno, marc in records.items()):
                # Nothing here differs from what is stored. Linking re-stores an
                # authority record for every catalogue record that points at it,
                # so most of these buffers are identical to the sector already on
                # disk, and writing one costs a zstd pass over the whole sector
                # plus an index row and a cache eviction per record in it.
                return
            existing_records.update(records)
            records = existing_records

        write_records_to_sector(self.db, base, sector_id, records)
