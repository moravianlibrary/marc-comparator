from sqlalchemy import Column, Integer, LargeBinary, SmallInteger, String

from adapters.database import Base

SECTOR_SIZE = 512  # 2^9


class MarcSector(Base):
    __tablename__ = "marc_sectors"

    base = Column(String, primary_key=True)
    sector_id = Column(Integer, primary_key=True)
    data = Column(LargeBinary, nullable=False)  # zstd-7 compressed
    record_count = Column(SmallInteger, nullable=False, default=0)


def sysno_to_sector_id(system_number: str) -> int:
    """Map a system number to its sector ID."""
    return int(system_number) // SECTOR_SIZE


def sector_sysno_range(sector_id: int) -> tuple[int, int]:
    """Return (start_sysno, end_sysno_exclusive) for a sector."""
    start = sector_id * SECTOR_SIZE
    return start, start + SECTOR_SIZE
