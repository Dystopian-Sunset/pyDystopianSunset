"""
Repository for CalendarYearCycle model.
"""

import logging

from ds_common.models.calendar_year_cycle import CalendarYearCycle
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class CalendarYearCycleRepository(BaseRepository[CalendarYearCycle]):
    """
    Repository for CalendarYearCycle model.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, CalendarYearCycle)
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def get_by_cycle_year(self, cycle_year: int) -> CalendarYearCycle | None:
        """
        Get a cycle year by its number.

        Args:
            cycle_year: Year in cycle (1-12)

        Returns:
            CalendarYearCycle instance or None
        """
        return await self.get_by_field("cycle_year", cycle_year)

    async def get_all_ordered(self) -> list[CalendarYearCycle]:
        """
        Get all cycle years ordered by cycle_year.

        Returns:
            List of CalendarYearCycle instances
        """
        all_cycles = await self.get_all()
        return sorted(all_cycles, key=lambda c: c.cycle_year)
