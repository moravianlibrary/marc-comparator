from sqlalchemy import (
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    SmallInteger,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from adapters.database import Base

SECTOR_SIZE = 1000


class MarcSector(Base):
    __tablename__ = "marc_sectors"

    base: Mapped[str] = mapped_column(String, primary_key=True)
    sector_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data: Mapped[bytes] = mapped_column(LargeBinary)  # zstd compressed blob
    record_count: Mapped[int] = mapped_column(SmallInteger, default=0)


class MarcRecordIndex(Base):
    __tablename__ = "marc_record_index"

    base: Mapped[str] = mapped_column(String, primary_key=True)
    system_number: Mapped[str] = mapped_column(String, primary_key=True)
    sector_id: Mapped[int] = mapped_column(Integer)
    offset_in_sector: Mapped[int] = mapped_column(Integer)
    record_length: Mapped[int] = mapped_column(Integer)

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
