import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ds_common.models.world_event import EventStatus, EventType, WorldEvent
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class WorldEventRepository(BaseRepository[WorldEvent]):
    """
    Repository for WorldEvent model.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, WorldEvent)
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def get_by_status(
        self, status: EventStatus, session: AsyncSession | None = None
    ) -> list[WorldEvent]:
        """
        Get all events with a specific status.

        Args:
            status: Event status to filter by
            session: Optional database session

        Returns:
            List of WorldEvent instances
        """
        stmt = select(WorldEvent).where(WorldEvent.status == status)

        async def _execute(sess: AsyncSession):
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)

    async def get_by_type(
        self, event_type: EventType, session: AsyncSession | None = None
    ) -> list[WorldEvent]:
        """
        Get all events of a specific type.

        Args:
            event_type: Event type to filter by
            session: Optional database session

        Returns:
            List of WorldEvent instances
        """
        stmt = select(WorldEvent).where(WorldEvent.event_type == event_type)

        async def _execute(sess: AsyncSession):
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)

    async def get_by_faction(
        self, faction: str, session: AsyncSession | None = None
    ) -> list[WorldEvent]:
        """
        Get all events affecting a specific faction.

        Args:
            faction: Faction name
            session: Optional database session

        Returns:
            List of WorldEvent instances
        """
        # Note: This requires array contains check - simplified for now
        # In production, you'd use proper array operators
        all_events = await self.get_all(session=session)
        return [e for e in all_events if faction in e.affected_factions]
