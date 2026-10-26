import logging
import threading
from collections import defaultdict
from collections.abc import Callable, Sequence

import zstandard as zstd
from marcdantic import MarcRecord
from marcdantic.context import MarcContext
from pydantic import ValidationError
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


class _ThreadLocalCompressor:
    """A zstd compressor per thread, behind the one interface every caller uses.

    python-zstandard instances must not be used from two threads at once, and
    sectors are read and written from several: FastAPI runs sync endpoints in a
    thread pool. One shared instance corrupted concurrent reads ("Data
    corruption detected") and could crash the process outright.
    """

    def __init__(self) -> None:
        self._local = threading.local()

    def compress(self, data: bytes) -> bytes:
        compressor = getattr(self._local, "compressor", None)
        if compressor is None:
            compressor = self._local.compressor = zstd.ZstdCompressor(level=ZSTD_LEVEL)
        return compressor.compress(data)


class _ThreadLocalDecompressor:
    """A zstd decompressor per thread, for the reason `_ThreadLocalCompressor` gives."""

    def __init__(self) -> None:
        self._local = threading.local()

    def decompress(self, data: bytes) -> bytes:
        decompressor = getattr(self._local, "decompressor", None)
        if decompressor is None:
            decompressor = self._local.decompressor = zstd.ZstdDecompressor()
        return decompressor.decompress(data)


_compressor = _ThreadLocalCompressor()
_decompressor = _ThreadLocalDecompressor()

CACHE_PREFIX = "marc:"


#: How to parse a record read back out of our own storage.
#:
#: The mandatory-field check belongs at the door, not on every read: a record
#: in sector storage was already accepted once, by whichever path put it there.
#: Re-imposing the default 001/005/008 on the way out would make a row we
#: chose to keep unreadable — and authority records harvested from the union
#: catalogue are admitted without 005 on purpose (CANDIDATE_MARC_CONTEXT),
#: so holding their stored form to a stricter rule than their accepted form
#: would fail every later read of a record that linked perfectly well.
STORED_MARC_CONTEXT = MarcContext(mandatory_fields=[])


def read_stored_marc(raw: bytes) -> MarcRecord:
    """Parse MARC bytes that came out of sector storage."""
    return MarcRecord.from_mrc(raw, STORED_MARC_CONTEXT)


#: Field errors quoted back to the caller. One is almost always the whole
#: story, and a record that fails validation in fifty places should not
#: answer with fifty lines of it.
REPORTED_MARC_ERRORS = 3


def describe_marc_errors(error: ValidationError) -> str:
    """Name the fields pydantic rejected, in the shape MARC people read.

    ``loc`` is already the path through the parsed record —
    ``("variable_fields", "500", 0, "ind1")`` is field 500, first occurrence,
    first indicator — so joining it says where to look without translation.

    Lives beside the reader rather than with one of its callers: every path
    that reads stored MARC can meet a record that parsed and would not
    validate, and they should all say the same thing about it.
    """

    reported = error.errors(include_url=False, include_context=False, include_input=False)
    described = [
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
        for item in reported[:REPORTED_MARC_ERRORS]
    ]
    if len(reported) > REPORTED_MARC_ERRORS:
        described.append(f"and {len(reported) - REPORTED_MARC_ERRORS} more")
    return "; ".join(described)


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


def read_marc_for_ids(db: Session, record_ids: Sequence[str]) -> dict[str, tuple[str, str, bytes]]:
    """MARC for a window of catalog records, keyed by record id.

    Every window in the system walks a list of record ids and wants each
    record's MARC. Done the obvious way that is a lookup of the row plus two
    more queries to find and decompress the MARC — three round trips per
    record, where a window shares almost all of its sectors.

    The base and system number come back with the bytes because the callers
    need them and would otherwise go back to the row for them. Nothing here is
    an ORM instance: ``handle_batch_progress_snippet`` cycles the session every
    ``commit_interval`` records, which detaches anything preloaded in bulk,
    and a tuple belongs to no session.

    Records with no MARC in storage are simply absent, as in ``read_marc``.
    """

    from entities.catalog_record import CatalogRecord

    rows = db.execute(
        select(CatalogRecord.id, CatalogRecord.base, CatalogRecord.system_number).where(
            CatalogRecord.id.in_(record_ids)
        )
    ).all()

    by_base: defaultdict[str, list[str]] = defaultdict(list)
    for _record_id, base, system_number in rows:
        by_base[base].append(system_number)

    marc = {
        (base, system_number): raw
        for base, system_numbers in by_base.items()
        for system_number, raw in read_marc_many(db, base, system_numbers).items()
    }

    found: dict[str, tuple[str, str, bytes]] = {}
    for record_id, base, system_number in rows:
        raw = marc.get((base, system_number))
        if raw is not None:
            found[record_id] = (base, system_number, raw)
    return found


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
