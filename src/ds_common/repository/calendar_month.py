"""
Repository for CalendarMonth model.
"""

import logging

from ds_common.models.calendar_month import CalendarMonth
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class CalendarMonthRepository(BaseRepository[CalendarMonth]):
    """
    Repository for CalendarMonth model.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, CalendarMonth)
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def get_by_month_number(self, month_number: int) -> CalendarMonth | None:
        """
        Get a month by its number.

        Args:
            month_number: Month number (1-18)

        Returns:
            CalendarMonth instance or None
        """
        return await self.get_by_field("month_number", month_number)

    async def get_all_ordered(self) -> list[CalendarMonth]:
        """
        Get all months ordered by month number.

        Returns:
            List of CalendarMonth instances
        """
        all_months = await self.get_all()
        return sorted(all_months, key=lambda m: m.month_number)
