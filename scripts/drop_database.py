#!/usr/bin/env python3
"""Drop the entire database."""

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
# Connect to postgres database to drop the target database
admin_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/postgres"


async def drop_database():
    """Drop the entire database."""
    try:
        engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
        # Use autocommit mode - DROP DATABASE cannot run in a transaction
        async with engine.connect() as conn:
            # Terminate any active connections to the database
            await conn.execute(
                text(
                    f"""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = '{database}'
                    AND pid <> pg_backend_pid()
                    """
                )
            )
            # Drop the database (must be autocommit)
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{database}"'))
            print(f"Dropped database '{database}'")
        await engine.dispose()
    except Exception as e:
        print(f"Error dropping database: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(drop_database())
