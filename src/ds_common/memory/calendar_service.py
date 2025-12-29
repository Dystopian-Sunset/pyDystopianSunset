import logging

from ds_common.memory.game_time_service import GameTimeService
from ds_common.models.calendar_event import CalendarEvent
from ds_common.models.world_memory import WorldMemory
from ds_common.repository.calendar_event import CalendarEventRepository
from ds_common.repository.world_memory import WorldMemoryRepository
from ds_discord_bot.postgres_manager import PostgresManager


class CalendarService:
    """
    Service for managing calendar events, recurring events, and regional variations.
    """

    def __init__(self, postgres_manager: PostgresManager, game_time_service: GameTimeService):
        self.postgres_manager = postgres_manager
        self.game_time_service = game_time_service
        self.calendar_repo = CalendarEventRepository(postgres_manager)
        self.world_memory_repo = WorldMemoryRepository(postgres_manager)
        self.logger = logging.getLogger(__name__)

    async def get_current_game_date(self) -> dict:
        """
        Get the current game date.

        Returns:
            Game date dict: {year, day, hour, season, day_of_week}
        """
        game_time = await self.game_time_service.get_current_game_time()
        # Use year_day (day of year 1-400) instead of game_day (day of month, can be None)
        # Calendar events use year day, not month day
        year_day = (
            game_time.year_day
            if hasattr(game_time, "year_day") and game_time.year_day is not None
            else (game_time.game_day if game_time.game_day is not None else 1)
        )
        return {
            "year": game_time.game_year,
            "day": year_day,
            "hour": game_time.game_hour,
            "season": game_time.season,
            "day_of_week": game_time.day_of_week,
        }

    async def is_event_active(self, event: CalendarEvent) -> bool:
        """
        Check if a calendar event is currently active.

        Args:
            event: CalendarEvent to check

        Returns:
            True if event is active, False otherwise
        """
        current_date = await self.get_current_game_date()
        start_time = event.start_game_time
        end_time = event.end_game_time

        # Ensure we have valid values (handle None cases)
        current_day = current_date.get("day")
        current_hour = current_date.get("hour")
        current_year = current_date.get("year")

        if current_day is None or current_hour is None or current_year is None:
            self.logger.warning(f"Invalid current_date values: {current_date}")
            return False

        start_day = start_time.get("day")
        start_hour = start_time.get("hour", 0)
        start_year = start_time.get("year")
        end_day = end_time.get("day")
        end_hour = end_time.get("hour", 29)

        if start_day is None or end_day is None:
            self.logger.warning(f"Invalid event time values: start={start_time}, end={end_time}")
            return False

        # For recurring events, check if current day/hour matches
        if event.is_recurring:
            # Check if year is specified (null means any year)
            if start_year is not None and current_year != start_year:
                return False

            # Check day and hour
            if current_day < start_day:
                return False
            if current_day > end_day:
                return False

            # Check hour range
            if current_day == start_day:
                if current_hour < start_hour:
                    return False
            if current_day == end_day:
                if current_hour > end_hour:
                    return False

            return True
        # Non-recurring event - check exact match
        if start_year is None or current_year != start_year:
            return False
        if current_day < start_day or current_day > end_day:
            return False
        if current_day == start_day and current_hour < start_hour:
            return False
        if current_day == end_day and current_hour > end_hour:
            return False

        return True

    async def get_upcoming_events(self, days_ahead: int = 7) -> list[CalendarEvent]:
        """
        Get upcoming calendar events within the specified days.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            List of upcoming CalendarEvent instances
        """
        current_date = await self.get_current_game_date()
        all_events = await self.calendar_repo.get_all()
        upcoming = []

        # Ensure we have valid current date values
        current_day = current_date.get("day")
        current_year = current_date.get("year")
        if current_day is None or current_year is None:
            self.logger.warning(
                f"Invalid current_date values in get_upcoming_events: {current_date}"
            )
            return []

        for event in all_events:
            start_time = event.start_game_time
            event_day = start_time.get("day")
            if event_day is None:
                continue  # Skip events with invalid day values

            # For recurring events, check if it occurs in the next N days
            if event.is_recurring:
                # Get days_per_year from game settings
                from ds_common.repository.game_settings import GameSettingsRepository

                settings_repo = GameSettingsRepository(self.postgres_manager)
                settings = await settings_repo.get_settings()
                days_per_year = settings.game_days_per_year

                # Check if event occurs in current year
                if (event_day >= current_day and event_day <= current_day + days_ahead) or (
                    current_day + days_ahead > days_per_year
                    and event_day <= (current_day + days_ahead) % days_per_year
                ):
                    upcoming.append(event)
            else:
                # Non-recurring - check if it's in the future
                event_year = start_time.get("year")
                if event_year is not None:
                    if event_year >= current_year:
                        if event_year == current_year:
                            if event_day >= current_day and event_day <= current_day + days_ahead:
                                upcoming.append(event)
                        else:
                            upcoming.append(event)

        return sorted(
            upcoming,
            key=lambda e: (
                e.start_game_time.get("year") or 0,
                e.start_game_time.get("day") or 1,
            ),
        )

    async def get_active_events(
        self, region: str | None = None, faction: str | None = None
    ) -> list[CalendarEvent]:
        """
        Get currently active calendar events, optionally filtered by region or faction.

        Args:
            region: Optional region name to filter by
            faction: Optional faction name to filter by

        Returns:
            List of active CalendarEvent instances
        """
        all_events = await self.calendar_repo.get_all()
        active = []

        for event in all_events:
            if await self.is_event_active(event):
                # Apply filters
                if faction and event.faction_specific:
                    if faction not in event.affected_factions:
                        continue

                # Apply region filter if specified
                if region:
                    # Events without regional_variations are global, include them
                    if event.regional_variations:
                        # Check if region matches any key in regional_variations
                        # Keys can be region names or region IDs (as strings)
                        region_matched = False
                        for region_key in event.regional_variations.keys():
                            # Direct match with region name
                            if region_key == region:
                                region_matched = True
                                break

                            # Try to match by region ID if region_key is a UUID string
                            try:
                                from ds_common.memory.region_service import RegionService

                                region_service = RegionService(self.postgres_manager)
                                region_obj = await region_service.region_repo.get_by_field(
                                    "name", region, case_sensitive=False
                                )

                                if region_obj and (
                                    str(region_obj.id) == region_key
                                    or region_key == region_obj.name
                                ):
                                    region_matched = True
                                    break
                            except Exception:
                                # If region lookup fails, continue checking other keys
                                pass

                        # Only include event if region matches
                        if not region_matched:
                            continue

                active.append(event)

        return active

    async def apply_regional_variations(self, event: CalendarEvent, region: str) -> dict:
        """
        Get regional variations for a calendar event.

        Args:
            event: CalendarEvent
            region: Region name

        Returns:
            Regional variation dict with name, description, etc.
        """
        if not event.regional_variations:
            return {"name": event.name, "description": event.description}

        variations = event.regional_variations
        if region in variations:
            return variations[region]

        return {"name": event.name, "description": event.description}

    async def create_event_memory(self, event: CalendarEvent) -> WorldMemory:
        """
        Create a world memory for an active calendar event.

        Args:
            event: CalendarEvent

        Returns:
            Created WorldMemory
        """
        game_time = await self.game_time_service.get_current_game_time()
        game_time_context = {
            "year": game_time.game_year,
            "day": game_time.game_day,
            "hour": game_time.game_hour,
            "season": game_time.season,
        }

        memory = WorldMemory(
            memory_category="event",
            title=f"{event.name} - Active",
            description=f"The calendar event '{event.name}' is currently active.",
            full_narrative=f"Calendar Event: {event.name}\nType: {event.event_type}\nDescription: {event.description or 'N/A'}",
            impact_level="minor",
            game_time_context=game_time_context,
        )

        return await self.world_memory_repo.create(memory)
