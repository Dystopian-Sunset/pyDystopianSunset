from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ds_common.models.world_memory import ImpactLevel, MemoryCategory, WorldMemory
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class WorldMemoryRepository(BaseRepository[WorldMemory]):
    """Repository for world memory operations."""

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, WorldMemory)

    async def semantic_search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        is_public: bool | None = None,
        dimensions: int | None = None,
        session: AsyncSession | None = None,
    ) -> list[tuple[WorldMemory, float]]:
        """
        Perform semantic search on world memories.

        Args:
            query_embedding: Query vector embedding
            limit: Maximum number of results
            is_public: Filter by public status (None = all)
            dimensions: Embedding dimensions (defaults to len(query_embedding))
            session: Optional database session

        Returns:
            List of tuples (WorldMemory, distance) where lower distance = more similar
        """
        # Determine dimensions from embedding if not provided
        if dimensions is None:
            dimensions = len(query_embedding)

        self.logger.debug(f"Performing semantic search with limit {limit}, dimensions {dimensions}")

        async def _execute(sess: AsyncSession):
            # Use pgvector cosine distance operator (<->)
            # Lower distance = more similar
            from pgvector.sqlalchemy import Vector
            from sqlalchemy import cast

            # Cast query embedding to Vector type with explicit dimensions
            # This matches the pattern used in other repositories
            query_vec = cast(query_embedding, Vector(dimensions))

            stmt = select(
                WorldMemory,
                (WorldMemory.embedding.op("<->")(query_vec)).label("distance"),
            )
            if is_public is not None:
                stmt = stmt.where(WorldMemory.is_public == is_public)
            stmt = stmt.where(WorldMemory.embedding.isnot(None))
            stmt = stmt.order_by("distance").limit(limit)
            result = await sess.execute(stmt)
            return [(row[0], row[1]) for row in result.all()]

        return await self._with_session(_execute, session)

    async def get_by_impact_level(
        self,
        impact_level: ImpactLevel,
        session: AsyncSession | None = None,
    ) -> list[WorldMemory]:
        """
        Get world memories by impact level.

        Args:
            impact_level: Impact level to filter by
            session: Optional database session

        Returns:
            List of world memories
        """
        self.logger.debug(f"Getting world memories with impact level {impact_level}")

        async def _execute(sess: AsyncSession):
            stmt = select(WorldMemory).where(WorldMemory.impact_level == impact_level)
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)

    async def get_by_category(
        self,
        category: MemoryCategory,
        session: AsyncSession | None = None,
    ) -> list[WorldMemory]:
        """
        Get world memories by category.

        Args:
            category: Memory category to filter by
            session: Optional database session

        Returns:
            List of world memories
        """
        self.logger.debug(f"Getting world memories with category {category}")

        async def _execute(sess: AsyncSession):
            stmt = select(WorldMemory).where(WorldMemory.memory_category == category)
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)

    async def get_related_entities(
        self,
        entity_type: Literal["characters", "locations", "factions"],
        entity_ids: list[str],
        session: AsyncSession | None = None,
    ) -> list[WorldMemory]:
        """
        Get world memories related to specific entities.

        Args:
            entity_type: Type of entity (characters, locations, factions)
            entity_ids: List of entity IDs/names
            session: Optional database session

        Returns:
            List of related world memories
        """
        self.logger.debug(f"Getting world memories for {entity_type} {entity_ids}")

        async def _execute(sess: AsyncSession):
            # Use JSONB containment operator (@>)
            stmt = select(WorldMemory).where(
                WorldMemory.related_entities[entity_type].astext.in_(entity_ids)  # type: ignore
            )
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)
