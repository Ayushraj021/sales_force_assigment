"""Alembic environment configuration."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, create_engine
from sqlalchemy.engine import Connection

from app.config import settings
from app.infrastructure.database.session import Base

# Import all models to ensure they are registered with Base.metadata
from app.infrastructure.database.models import (
    User,
    Role,
    Permission,
    Organization,
    APIKey,
    AuditLog,
    DataSource,
    Dataset,
    DataVersion,
    Channel,
    Metric,
    Model,
    ModelVersion,
    ModelParameter,
    AdstockConfig,
    SaturationConfig,
    Experiment,
    ExperimentRun,
    BudgetScenario,
    OptimizationConstraint,
    OptimizationResult,
    BudgetAllocation,
    Dashboard,
    Widget,
    Report,
    ScheduledReport,
    Export,
)

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for 'autogenerate'
target_metadata = Base.metadata

# Override sqlalchemy.url with our settings
config.set_main_option("sqlalchemy.url", settings.sync_database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with a connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using sync engine."""
    connectable = create_engine(
        settings.sync_database_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
