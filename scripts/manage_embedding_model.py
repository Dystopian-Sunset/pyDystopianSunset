#!/usr/bin/env python3
"""
Utility script to manage embedding model changes and database schema updates.

This script helps you:
1. Check current embedding configuration vs database schema
2. Generate and apply migrations for dimension changes
3. Optionally regenerate embeddings for existing records

Usage:
    python scripts/manage_embedding_model.py check
    python scripts/manage_embedding_model.py migrate --dimensions 768
    python scripts/manage_embedding_model.py regenerate --dry-run
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ds_common.config_bot import get_config
from ds_discord_bot.postgres_manager import PostgresManager

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%S:%M",
)
logger = logging.getLogger(__name__)


async def check_dimensions() -> None:
    """Check current configuration vs database schema."""
    config = get_config()
    desired_dimensions = config.ai_embedding_dimensions
    desired_model = config.ai_embedding_model

    logger.info("Configuration:")
    logger.info(f"  Model: {desired_model}")
    logger.info(f"  Dimensions: {desired_dimensions}")

    # Check database schema
    postgres_manager = await PostgresManager.create(
        host=config.postgres_host,
        port=config.postgres_port,
        database=config.postgres_database,
        user=config.postgres_user,
        password=config.postgres_password,
        pool_size=1,
        max_overflow=0,
        echo=False,
    )

    try:
        async with postgres_manager.get_session() as session:
            # Check actual column dimensions in database
            from sqlalchemy import text

            tables_to_check = [
                "world_memories",
                "episode_memories",
                "npc_memories",
                "game_history_embeddings",
            ]

            logger.info("\nDatabase Schema:")
            mismatches = []

            for table in tables_to_check:
                try:
                    result = await session.execute(
                        text(f"""
                            SELECT 
                                column_name,
                                udt_name,
                                (SELECT format_type(atttypid, atttypmod) 
                                 FROM pg_attribute 
                                 WHERE attrelid = '{table}'::regclass 
                                 AND attname = 'embedding') as column_type
                            FROM information_schema.columns
                            WHERE table_name = '{table}' 
                            AND column_name = 'embedding'
                        """)
                    )
                    row = result.first()
                    if row:
                        column_type = row.column_type
                        # Extract dimensions from vector(768) format
                        if "vector" in column_type.lower():
                            import re

                            match = re.search(r"vector\((\d+)\)", column_type.lower())
                            if match:
                                db_dimensions = int(match.group(1))
                                logger.info(
                                    f"  {table}.embedding: {column_type} ({db_dimensions} dimensions)"
                                )

                                if db_dimensions != desired_dimensions:
                                    mismatches.append((table, db_dimensions, desired_dimensions))
                            else:
                                logger.warning(
                                    f"  {table}.embedding: {column_type} (could not parse dimensions)"
                                )
                        else:
                            logger.warning(
                                f"  {table}.embedding: {column_type} (not a vector type)"
                            )
                    else:
                        logger.warning(f"  {table}.embedding: column not found")
                except Exception as e:
                    logger.warning(f"  {table}: Error checking - {e}")

            if mismatches:
                logger.warning("\n⚠️  MISMATCH DETECTED:")
                for table, db_dims, config_dims in mismatches:
                    logger.warning(
                        f"  {table}: Database has {db_dims} dimensions, config wants {config_dims}"
                    )
                logger.warning(
                    "\nRun 'python scripts/manage_embedding_model.py migrate' to fix this."
                )
            else:
                logger.info("\n✅ Configuration matches database schema!")

    finally:
        await postgres_manager.close()


async def count_embeddings() -> dict[str, int]:
    """Count embeddings in each table."""
    config = get_config()
    postgres_manager = await PostgresManager.create(
        host=config.postgres_host,
        port=config.postgres_port,
        database=config.postgres_database,
        user=config.postgres_user,
        password=config.postgres_password,
        pool_size=1,
        max_overflow=0,
        echo=False,
    )

    counts = {}
    try:
        async with postgres_manager.get_session() as session:
            from sqlalchemy import text

            tables = [
                "world_memories",
                "episode_memories",
                "npc_memories",
                "game_history_embeddings",
            ]

            for table in tables:
                result = await session.execute(
                    text(f"SELECT COUNT(*) FROM {table} WHERE embedding IS NOT NULL")
                )
                count = result.scalar()
                counts[table] = count or 0

    finally:
        await postgres_manager.close()

    return counts


def generate_migration(dimensions: int) -> None:
    """Generate a migration file for dimension change."""
    import subprocess
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    migration_name = f"change_embedding_dimensions_to_{dimensions}"

    logger.info(f"Generating migration: {migration_name}")

    # Run alembic revision
    result = subprocess.run(
        ["uv", "run", "alembic", "revision", "-m", migration_name],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        logger.error(f"Failed to generate migration: {result.stderr}")
        return

    logger.info("Migration file created. Please edit it to update vector dimensions.")
    logger.info("Then run: uv run alembic upgrade head")


async def regenerate_embeddings(dry_run: bool = True) -> None:
    """Regenerate embeddings for existing records."""
    config = get_config()

    if dry_run:
        logger.info("DRY RUN: Would regenerate embeddings for:")
        counts = await count_embeddings()
        total = sum(counts.values())
        for table, count in counts.items():
            if count > 0:
                logger.info(f"  {table}: {count} records")
        logger.info(f"  Total: {total} records")
        logger.info("\nRun with --no-dry-run to actually regenerate embeddings.")
        return

    logger.warning("⚠️  Regenerating embeddings will overwrite existing data!")
    logger.warning("This may take a while and use API credits.")

    response = input("Continue? (yes/no): ")
    if response.lower() != "yes":
        logger.info("Cancelled.")
        return

    # Initialize embedding service
    import redis.asyncio as redis
    from openai import AsyncOpenAI

    from ds_common.memory.embedding_service import EmbeddingService

    client_kwargs = {
        "api_key": config.ai_embedding_api_key
        if config.ai_embedding_api_key
        else "sk-ollama-local-dummy-key-not-used"
    }
    if config.ai_embedding_base_url:
        client_kwargs["base_url"] = config.ai_embedding_base_url

    openai_client = AsyncOpenAI(**client_kwargs)

    redis_client = None
    try:
        redis_client = redis.from_url(config.redis_url)
    except Exception:
        logger.warning("Redis not available, embeddings won't be cached")

    embedding_service = EmbeddingService(
        openai_client,
        redis_client,
        model=config.ai_embedding_model,
        dimensions=config.ai_embedding_dimensions,
    )

    # Initialize postgres
    postgres_manager = await PostgresManager.create(
        host=config.postgres_host,
        port=config.postgres_port,
        database=config.postgres_database,
        user=config.postgres_user,
        password=config.postgres_password,
        pool_size=5,
        max_overflow=10,
        echo=False,
    )

    try:
        # Regenerate world memories
        from ds_common.repository.world_memory import WorldMemoryRepository

        world_repo = WorldMemoryRepository(postgres_manager)

        async with postgres_manager.get_session() as session:
            from sqlalchemy import select

            from ds_common.models.world_memory import WorldMemory

            stmt = select(WorldMemory).where(WorldMemory.embedding.isnot(None))
            result = await session.execute(stmt)
            world_memories = result.scalars().all()

            logger.info(f"Regenerating {len(world_memories)} world memories...")
            for i, wm in enumerate(world_memories, 1):
                if i % 10 == 0:
                    logger.info(f"  Progress: {i}/{len(world_memories)}")

                text = f"{wm.title}\n{wm.description}\n{wm.full_narrative or ''}"
                new_embedding = await embedding_service.generate(text)
                wm.embedding = new_embedding
                await session.commit()

            logger.info("✅ World memories regenerated")

        # Regenerate episode memories
        from ds_common.repository.episode_memory import EpisodeMemoryRepository

        episode_repo = EpisodeMemoryRepository(postgres_manager)

        async with postgres_manager.get_session() as session:
            from sqlalchemy import select

            from ds_common.models.episode_memory import EpisodeMemory

            stmt = select(EpisodeMemory).where(EpisodeMemory.embedding.isnot(None))
            result = await session.execute(stmt)
            episodes = result.scalars().all()

            logger.info(f"Regenerating {len(episodes)} episode memories...")
            for i, ep in enumerate(episodes, 1):
                if i % 10 == 0:
                    logger.info(f"  Progress: {i}/{len(episodes)}")

                text = f"{ep.title}\n{ep.one_sentence_summary}\n{ep.summary or ''}"
                new_embedding = await embedding_service.generate(text)
                ep.embedding = new_embedding
                await session.commit()

            logger.info("✅ Episode memories regenerated")

        logger.info("\n✅ All embeddings regenerated!")

    finally:
        await postgres_manager.close()
        if redis_client:
            await redis_client.close()


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Manage embedding model configuration and database schema"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Check command
    check_parser = subparsers.add_parser("check", help="Check configuration vs database schema")

    # Migrate command
    migrate_parser = subparsers.add_parser(
        "migrate", help="Generate migration for dimension change"
    )
    migrate_parser.add_argument(
        "--dimensions",
        type=int,
        help="Target dimensions (default: from config)",
    )

    # Regenerate command
    regenerate_parser = subparsers.add_parser(
        "regenerate", help="Regenerate embeddings for existing records"
    )
    regenerate_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Show what would be regenerated without doing it (default: True)",
    )
    regenerate_parser.add_argument(
        "--no-dry-run",
        action="store_false",
        dest="dry_run",
        help="Actually regenerate embeddings",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "check":
        asyncio.run(check_dimensions())
    elif args.command == "migrate":
        if args.dimensions:
            generate_migration(args.dimensions)
        else:
            config = get_config()
            generate_migration(config.ai_embedding_dimensions)
    elif args.command == "regenerate":
        asyncio.run(regenerate_embeddings(dry_run=args.dry_run))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
