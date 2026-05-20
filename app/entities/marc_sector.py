from sqlalchemy import Column, ForeignKeyConstraint, Index, Integer, LargeBinary, SmallInteger, String

from adapters.database import Base

SECTOR_SIZE = 1000


class MarcSector(Base):
    __tablename__ = "marc_sectors"

    base = Column(String, primary_key=True)
    sector_id = Column(Integer, primary_key=True)
    data = Column(LargeBinary, nullable=False)  # zstd compressed blob
    record_count = Column(SmallInteger, nullable=False, default=0)


class MarcRecordIndex(Base):
    __tablename__ = "marc_record_index"

    base = Column(String, primary_key=True)
    system_number = Column(String, primary_key=True)
    sector_id = Column(Integer, nullable=False)
    offset_in_sector = Column(Integer, nullable=False)
    record_length = Column(Integer, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["base", "sector_id"],
            ["marc_sectors.base", "marc_sectors.sector_id"],
        ),
        Index("ix_marc_record_index_sector", "base", "sector_id"),
    )


def sysno_to_sector_id(system_number: str) -> int:
    return int(system_number) // SECTOR_SIZE


def sector_sysno_range(sector_id: int) -> tuple[int, int]:
    start = sector_id * SECTOR_SIZE
    return start, start + SECTOR_SIZE
