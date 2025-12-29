import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ds_common.models.calendar_event import CalendarEvent, CalendarEventType
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class CalendarEventRepository(BaseRepository[CalendarEvent]):
    """
    Repository for CalendarEvent model.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, CalendarEvent)
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def get_by_type(
        self, event_type: CalendarEventType, session: AsyncSession | None = None
    ) -> list[CalendarEvent]:
        """
        Get all calendar events of a specific type.

        Args:
            event_type: Calendar event type
            session: Optional database session

        Returns:
            List of CalendarEvent instances
        """
        stmt = select(CalendarEvent).where(CalendarEvent.event_type == event_type)

        async def _execute(sess: AsyncSession):
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)

    async def get_recurring(self, session: AsyncSession | None = None) -> list[CalendarEvent]:
        """
        Get all recurring calendar events.

        Args:
            session: Optional database session

        Returns:
            List of CalendarEvent instances
        """
        stmt = select(CalendarEvent).where(CalendarEvent.is_recurring == True)  # noqa: E712

        async def _execute(sess: AsyncSession):
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)

    async def get_by_faction(
        self, faction: str, session: AsyncSession | None = None
    ) -> list[CalendarEvent]:
        """
        Get all calendar events for a specific faction.

        Args:
            faction: Faction name
            session: Optional database session

        Returns:
            List of CalendarEvent instances
        """
        stmt = select(CalendarEvent).where(CalendarEvent.faction_specific == True)  # noqa: E712

        async def _execute(sess: AsyncSession):
            result = await sess.execute(stmt)
            events = list(result.scalars().all())
            return [e for e in events if faction in e.affected_factions]

        return await self._with_session(_execute, session)
