from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

from config import config as app_config

# Import all entity modules so Base.metadata knows about every table
from adapters.database import Base
from entities.authority_link import AuthorityLink  # noqa: F401
from entities.catalog_record import CatalogRecord  # noqa: F401
from entities.comparison import Comparison  # noqa: F401
from entities.marc_sector import MarcRecordIndex, MarcSector  # noqa: F401
from entities.record_review import RecordReview  # noqa: F401
from entities.result_snapshot import ResultSnapshot  # noqa: F401
from entities.role import Role  # noqa: F401
from entities.settings import Settings  # noqa: F401
from entities.task import Task  # noqa: F401
from entities.user import User, UserRole  # noqa: F401
from entities.validation import Validation  # noqa: F401

alembic_config = context.config

if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

target_metadata = Base.metadata

# Tables managed outside SQLAlchemy ORM (Celery, runtime-created analytics/facet tables)
EXCLUDE_TABLES = {
    "celery_taskmeta",
    "celery_tasksetmeta",
    "catalog_records_analytics",
    "facet_cube",
    "facet_cube_histogram",
}


def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name in EXCLUDE_TABLES:
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emits SQL to stdout."""
    context.configure(
        url=app_config.postgres.url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — connects to the database."""
    configuration = alembic_config.get_section(alembic_config.config_ini_section, {})
    configuration["sqlalchemy.url"] = app_config.postgres.url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
