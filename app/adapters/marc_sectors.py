from collections import defaultdict

import zstandard as zstd
from marcdantic import MarcRecord
from sqlalchemy.orm import Session

from entities.marc_sector import MarcSector, SECTOR_SIZE, sysno_to_sector_id

ZSTD_LEVEL = 7

_compressor = zstd.ZstdCompressor(level=ZSTD_LEVEL)
_decompressor = zstd.ZstdDecompressor()


def read_marc(db: Session, base: str, system_number: str) -> bytes | None:
    """Read a single MARC record from its sector."""
    sector_id = sysno_to_sector_id(system_number)
    sector = db.get(MarcSector, (base, sector_id))
    if sector is None:
        return None

    raw = _decompressor.decompress(sector.data)
    return _find_record_in_blob(raw, system_number)


def write_records_to_sector(
    db: Session,
    base: str,
    sector_id: int,
    records: dict[str, bytes],
) -> MarcSector:
    """Write/overwrite a full sector. `records` maps system_number -> raw MARC bytes.

    Records are sorted by sysno and concatenated before compression.
    """
    sorted_items = sorted(records.items(), key=lambda kv: int(kv[0]))
    blob = b"".join(marc for _, marc in sorted_items)
    compressed = _compressor.compress(blob)

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

    return sector


def upsert_record_in_sector(
    db: Session, base: str, system_number: str, marc_bytes: bytes
) -> None:
    """Insert or replace a single record within its sector."""
    sector_id = sysno_to_sector_id(system_number)
    sector = db.get(MarcSector, (base, sector_id))

    if sector is None:
        compressed = _compressor.compress(marc_bytes)
        sector = MarcSector(
            base=base, sector_id=sector_id,
            data=compressed, record_count=1,
        )
        db.add(sector)
        return

    # Decompress, parse all records, replace/add, recompress
    raw = _decompressor.decompress(sector.data)
    records = _parse_blob_to_dict(raw)
    records[system_number] = marc_bytes
    write_records_to_sector(db, base, sector_id, records)


def _find_record_in_blob(blob: bytes, target_sysno: str) -> bytes | None:
    """Walk concatenated MARC records, return the one matching target_sysno (via 001 field)."""
    offset = 0
    while offset < len(blob):
        rec_len = int(blob[offset:offset + 5])
        rec_bytes = blob[offset:offset + rec_len]
        rec = MarcRecord.from_mrc(rec_bytes)
        if rec.control_fields_selector.system_number == target_sysno:
            return rec_bytes
        offset += rec_len
    return None


def _parse_blob_to_dict(blob: bytes) -> dict[str, bytes]:
    """Parse concatenated MARC blob into {system_number: bytes}."""
    records = {}
    offset = 0
    while offset < len(blob):
        rec_len = int(blob[offset:offset + 5])
        rec_bytes = blob[offset:offset + rec_len]
        rec = MarcRecord.from_mrc(rec_bytes)
        sysno = rec.control_fields_selector.system_number
        records[sysno] = rec_bytes
        offset += rec_len
    return records


class SectorBuffer:
    """Accumulates records per (base, sector_id) and flushes whole sectors."""

    def __init__(self, db: Session, flush_threshold: int = SECTOR_SIZE):
        self.db = db
        self.flush_threshold = flush_threshold
        self._buffers: dict[tuple[str, int], dict[str, bytes]] = defaultdict(dict)

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
            existing_records = _parse_blob_to_dict(
                _decompressor.decompress(existing.data)
            )
            existing_records.update(records)
            records = existing_records

        write_records_to_sector(self.db, base, sector_id, records)
