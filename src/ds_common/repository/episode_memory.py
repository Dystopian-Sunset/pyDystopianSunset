from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ds_common.models.episode_memory import EpisodeMemory
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class EpisodeMemoryRepository(BaseRepository[EpisodeMemory]):
    """Repository for episode memory operations."""

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, EpisodeMemory)

    async def get_by_characters(
        self,
        character_ids: list[UUID],
        session: AsyncSession | None = None,
    ) -> list[EpisodeMemory]:
        """
        Get episodes involving specific characters.

        Args:
            character_ids: List of character IDs
            session: Optional database session

        Returns:
            List of episode memories
        """
        self.logger.debug(f"Getting episodes for characters {character_ids}")

        async def _execute(sess: AsyncSession):
            # Use array overlap operator to find episodes with any of these characters
            stmt = (
                select(EpisodeMemory)
                .where(
                    EpisodeMemory.characters.overlap(character_ids),  # type: ignore
                    EpisodeMemory.promoted_to_world == False,  # noqa: E712
                )
                .order_by(EpisodeMemory.created_at.desc())
            )
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)

    async def get_by_locations(
        self,
        location_ids: list[UUID],
        session: AsyncSession | None = None,
    ) -> list[EpisodeMemory]:
        """
        Get episodes involving specific locations.

        Args:
            location_ids: List of location IDs
            session: Optional database session

        Returns:
            List of episode memories
        """
        self.logger.debug(f"Getting episodes for locations {location_ids}")

        async def _execute(sess: AsyncSession):
            stmt = (
                select(EpisodeMemory)
                .where(
                    EpisodeMemory.locations.overlap(location_ids),  # type: ignore
                    EpisodeMemory.promoted_to_world == False,  # noqa: E712
                )
                .order_by(EpisodeMemory.created_at.desc())
            )
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)

    async def get_unpromoted(
        self,
        session: AsyncSession | None = None,
    ) -> list[EpisodeMemory]:
        """
        Get all unpromoted episode memories.

        Args:
            session: Optional database session

        Returns:
            List of unpromoted episode memories
        """
        self.logger.debug("Getting unpromoted episode memories")

        async def _execute(sess: AsyncSession):
            stmt = (
                select(EpisodeMemory)
                .where(
                    EpisodeMemory.promoted_to_world == False  # noqa: E712
                )
                .order_by(EpisodeMemory.created_at.desc())
            )
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)

    async def get_expired(
        self,
        session: AsyncSession | None = None,
    ) -> list[EpisodeMemory]:
        """
        Get all expired episode memories.

        Args:
            session: Optional database session

        Returns:
            List of expired episode memories
        """
        self.logger.debug("Getting expired episode memories")

        async def _execute(sess: AsyncSession):
            # Convert timezone-aware datetime to naive UTC for comparison with TIMESTAMP WITHOUT TIME ZONE
            now_naive = datetime.now(UTC).replace(tzinfo=None)
            stmt = select(EpisodeMemory).where(
                EpisodeMemory.expires_at < now_naive,
                EpisodeMemory.promoted_to_world == False,  # noqa: E712
            )
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)
