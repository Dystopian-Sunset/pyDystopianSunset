import asyncio
import os
import warnings
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SAWarning
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Suppress the cycle warning for characters/players circular foreign keys
# This is expected and handled in the migration by creating tables in the correct order
warnings.filterwarnings(
    "ignore",
    message=".*Cannot correctly sort tables.*characters.*players.*",
    category=SAWarning,
)

# Load environment variables
load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models to ensure they are registered with SQLAlchemy metadata
# This import must happen after dotenv is loaded
import sys
from pathlib import Path

# Add the project root to the path so we can import from src
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Import all models to ensure they are registered with SQLAlchemy metadata
from sqlmodel import SQLModel  # noqa: E402

# Get metadata from SQLModel - all models with table=True are registered here
target_metadata = SQLModel.metadata


# Build database URL from environment variables
def get_database_url() -> str:
    """
    Build database URL from environment variables.

    Returns:
        Database URL in format: postgresql+asyncpg://user:pass@host:port/dbname
    """
    host = os.getenv("DS_POSTGRES_HOST", "localhost")
    port = os.getenv("DS_POSTGRES_PORT", "5432")
    database = os.getenv("DS_POSTGRES_DATABASE", "game")
    user = os.getenv("DS_POSTGRES_USER", "postgres")
    password = os.getenv("DS_POSTGRES_PASSWORD", "postgres")

    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Run migrations with the given connection.

    Args:
        connection: SQLAlchemy connection
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        transaction_per_migration=True,  # Each migration in its own transaction
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in async mode.

    Creates an async engine and runs migrations.
    """
    url = get_database_url()
    connectable = create_async_engine(
        url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
