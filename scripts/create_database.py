#!/usr/bin/env python3
"""Create a new empty database."""

import asyncio
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

host = os.getenv("DS_POSTGRES_HOST", "localhost")
port = os.getenv("DS_POSTGRES_PORT", "5432")
database = os.getenv("DS_POSTGRES_DATABASE", "game")
user = os.getenv("DS_POSTGRES_USER", "postgres")
password = os.getenv("DS_POSTGRES_PASSWORD", "postgres")
# Connect to postgres database to create the target database
admin_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/postgres"


async def create_database():
    """Create a new empty database."""
    try:
        engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
        # Use autocommit mode - CREATE DATABASE cannot run in a transaction
        async with engine.connect() as conn:
            # Create the database (must be autocommit)
            await conn.execute(text(f'CREATE DATABASE "{database}"'))
            print(f"Created database '{database}'")
        await engine.dispose()

        # Now connect to the new database and enable extensions
        db_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
        db_engine = create_async_engine(db_url)
        async with db_engine.connect() as conn:
            # Enable pgvector extension
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.commit()
            print("Enabled pgvector extension")
        await db_engine.dispose()
    except Exception as e:
        print(f"Error creating database: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(create_database())
