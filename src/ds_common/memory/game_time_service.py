import logging
from datetime import UTC, datetime, timedelta

from ds_common.models.game_time import GameTime, Season
from ds_common.repository.game_settings import GameSettingsRepository
from ds_common.repository.game_time import GameTimeRepository
from ds_discord_bot.postgres_manager import PostgresManager


class GameTimeService:
    """
    Service for managing game time calculations and conversions.
    """

    def __init__(self, postgres_manager: PostgresManager):
        self.postgres_manager = postgres_manager
        self.repository = GameTimeRepository(postgres_manager)
        self.settings_repository = GameSettingsRepository(postgres_manager)
        self.logger = logging.getLogger(__name__)

    async def _get_settings(self):
        """Get game settings (cached for performance)."""
        return await self.settings_repository.get_settings()

    def _get_seasonal_day_night_hours(self, game_time: GameTime, settings) -> tuple[int, int]:
        """
        Get day_start and night_start hours for the current season.

        Args:
            game_time: Current game time
            settings: Game settings

        Returns:
            Tuple of (day_start_hour, night_start_hour) for current season
        """
        # Get seasonal day/night configuration
        seasonal_config = game_time.game_time_config.get("seasonal_day_night", {})
        current_season = game_time.season or "SPRING"

        # Get seasonal hours if configured, otherwise use base settings
        season_hours = seasonal_config.get(current_season, {})
        day_start = season_hours.get("day_start", settings.game_day_start_hour)
        night_start = season_hours.get("night_start", settings.game_night_start_hour)

        return day_start, night_start

    async def get_current_game_time(self) -> GameTime:
        """
        Get the current game time record, initializing if needed.

        Returns:
            GameTime instance
        """
        game_time = await self.repository.get_game_time()
        if not game_time:
            game_time = await self.repository.initialize_game_time()
            # Initialize epoch_start in settings if not set (migration from GameTime)
            settings = await self._get_settings()
            if not settings.game_epoch_start:
                settings.game_epoch_start = game_time.current_game_time
                await self.settings_repository.update(settings)

        # Normalize datetimes to be timezone-aware (UTC)
        if game_time.current_game_time.tzinfo is None:
            # If naive, assume it's UTC and make it aware
            game_time.current_game_time = game_time.current_game_time.replace(tzinfo=UTC)

        # Normalize epoch_start in settings if needed
        settings = await self._get_settings()
        if settings.game_epoch_start and settings.game_epoch_start.tzinfo is None:
            settings.game_epoch_start = settings.game_epoch_start.replace(tzinfo=UTC)
            await self.settings_repository.update(settings)

        if game_time.last_shutdown_time and game_time.last_shutdown_time.tzinfo is None:
            # If naive, assume it's UTC and make it aware
            game_time.last_shutdown_time = game_time.last_shutdown_time.replace(tzinfo=UTC)

        # Initialize year_day from game_day if needed (backward compatibility)
        if not hasattr(game_time, "year_day") or game_time.year_day is None:
            if hasattr(game_time, "game_day") and game_time.game_day:
                game_time.year_day = game_time.game_day

        # Calculate cycle_year if not set
        if not hasattr(game_time, "cycle_year") or game_time.cycle_year is None:
            if game_time.game_year:
                game_time.cycle_year = ((game_time.game_year - 1) % 12) + 1

        return game_time

    async def get_season(self) -> Season:
        """
        Get the current season.

        Returns:
            Current season
        """
        game_time = await self.get_current_game_time()
        return game_time.season or "SPRING"

    async def is_daytime(self) -> bool:
        """
        Check if it's currently daytime.

        Returns:
            True if daytime, False if nighttime
        """
        game_time = await self.get_current_game_time()
        return game_time.is_daytime

    async def get_current_month_name(self) -> str | None:
        """
        Get the name of the current month.

        Returns:
            Month name or None if not available
        """
        game_time = await self.get_current_game_time()
        if not game_time.game_month:
            return None

        from ds_common.repository.calendar_month import CalendarMonthRepository

        month_repo = CalendarMonthRepository(self.postgres_manager)
        month = await month_repo.get_by_month_number(game_time.game_month)
        return month.name if month else None

    async def get_current_cycle_animal(self) -> str | None:
        """
        Get the animal name for the current cycle year.

        Returns:
            Animal name or None if not available
        """
        game_time = await self.get_current_game_time()
        if not game_time.cycle_year:
            return None

        from ds_common.repository.calendar_year_cycle import CalendarYearCycleRepository

        cycle_repo = CalendarYearCycleRepository(self.postgres_manager)
        cycle_year = await cycle_repo.get_by_cycle_year(game_time.cycle_year)
        return cycle_year.animal_name if cycle_year else None

    async def get_time_of_day(self) -> str:
        """
        Get a description of the time of day.

        Returns:
            Time of day description (dawn, morning, noon, afternoon, dusk, night, midnight)
        """
        game_time = await self.get_current_game_time()
        hour = game_time.game_hour
        settings = await self._get_settings()
        _, night_start = self._get_seasonal_day_night_hours(game_time, settings)

        if hour < 3:
            return "midnight"
        if hour < 6:
            return "dawn"
        if hour < 10:
            return "morning"
        if hour < 14:
            return "noon"
        if hour < night_start:
            return "afternoon"
        if hour < 22:
            return "dusk"
        return "night"

    async def advance_game_time(self, real_minutes: float = 1.0) -> GameTime:
        """
        Advance game time based on real time elapsed.

        Args:
            real_minutes: Real minutes elapsed (default: 1.0)

        Returns:
            Updated GameTime instance
        """
        game_time = await self.get_current_game_time()
        settings = await self._get_settings()
        multiplier = settings.game_time_multiplier

        # Get config values from settings and game_time_config
        hours_per_day = settings.game_hours_per_day
        days_per_year = settings.game_days_per_year
        months_per_year = game_time.game_time_config.get("months_per_year", 20)
        days_per_month = game_time.game_time_config.get("days_per_month", 20)
        season_days = game_time.game_time_config.get(
            "season_days", {"SPRING": 100, "SUMMER": 100, "FALL": 100, "WINTER": 100}
        )

        # Calculate game hours to advance
        game_hours_to_advance = real_minutes * multiplier

        # Advance game time
        current_hour = game_time.game_hour
        current_year_day = (
            game_time.year_day
            if hasattr(game_time, "year_day") and game_time.year_day
            else (
                game_time.game_day if hasattr(game_time, "game_day") and game_time.game_day else 1
            )
        )
        current_year = game_time.game_year
        current_minute = game_time.game_minute

        # Add minutes first
        total_minutes = current_minute + (game_hours_to_advance * 60)
        new_minute = int(total_minutes % 60)
        additional_hours = int(total_minutes // 60)

        # Add hours
        new_hour = (current_hour + additional_hours) % hours_per_day
        additional_days = (current_hour + additional_hours) // hours_per_day

        # Add days (year_day tracks day of year 1-400)
        new_year_day = ((current_year_day - 1 + additional_days) % days_per_year) + 1
        additional_years = (current_year_day - 1 + additional_days) // days_per_year

        # Add years
        new_year = current_year + additional_years

        # Update game time
        game_time.game_hour = new_hour
        game_time.game_minute = new_minute
        game_time.year_day = new_year_day
        game_time.game_year = new_year

        # Always use timezone-aware datetime (UTC)
        game_time.current_game_time = datetime.now(UTC)

        # Update season (based on year_day) - do this before calculating day/night
        spring_days = season_days.get("SPRING", 100)
        summer_days = season_days.get("SUMMER", 100)
        fall_days = season_days.get("FALL", 100)

        if new_year_day <= spring_days:
            game_time.season = "SPRING"
        elif new_year_day <= spring_days + summer_days:
            game_time.season = "SUMMER"
        elif new_year_day <= spring_days + summer_days + fall_days:
            game_time.season = "FALL"
        else:
            game_time.season = "WINTER"

        # Update day/night using seasonal hours
        day_start, night_start = self._get_seasonal_day_night_hours(game_time, settings)
        game_time.is_daytime = day_start <= new_hour < night_start

        # Update day of week (simplified - 7 day week)
        days_since_epoch = (new_year - 1) * days_per_year + (new_year_day - 1)
        day_of_week_num = days_since_epoch % 7
        days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
        game_time.day_of_week = days[day_of_week_num]

        # Get month definitions from database
        from ds_common.repository.calendar_month import CalendarMonthRepository

        month_repo = CalendarMonthRepository(self.postgres_manager)
        all_months = await month_repo.get_all_ordered()

        if all_months:
            # Use actual month definitions from database
            cumulative_days = 0
            calculated_month = 1
            month_day = 1
            for month in all_months:
                month_start_day = cumulative_days + 1
                month_end_day = cumulative_days + month.days
                if month_start_day <= new_year_day <= month_end_day:
                    calculated_month = month.month_number
                    month_day = new_year_day - cumulative_days
                    break
                cumulative_days += month.days
            # If we didn't find a month (shouldn't happen, but fallback)
            if calculated_month == 1 and new_year_day > sum(m.days for m in all_months):
                calculated_month = months_per_year
                month_day = new_year_day - sum(m.days for m in all_months[:-1])
            game_time.game_month = calculated_month
            game_time.game_day = month_day
        else:
            # Fallback: calculate month based on average days per month
            calculated_month = ((new_year_day - 1) // days_per_month) + 1
            if calculated_month > months_per_year:
                calculated_month = months_per_year
            game_time.game_month = calculated_month
            game_time.game_day = ((new_year_day - 1) % days_per_month) + 1

        # Calculate cycle year (1-12) based on game year
        cycle_year = ((new_year - 1) % 12) + 1
        game_time.cycle_year = cycle_year

        return await self.repository.update_game_time(game_time)

    async def convert_real_to_game_time(self, real_time: datetime) -> dict:
        """
        Convert a real datetime to game time.

        Args:
            real_time: Real datetime

        Returns:
            Game time dict: {year, day, hour, minute, season}
        """
        game_time = await self.get_current_game_time()
        settings = await self._get_settings()
        epoch_start = settings.game_epoch_start or game_time.current_game_time
        multiplier = settings.game_time_multiplier

        # Get config values from settings
        hours_per_day = settings.game_hours_per_day
        days_per_year = settings.game_days_per_year
        months_per_year = game_time.game_time_config.get("months_per_year", 20)
        days_per_month = game_time.game_time_config.get("days_per_month", 20)
        season_days = game_time.game_time_config.get(
            "season_days", {"SPRING": 100, "SUMMER": 100, "FALL": 100, "WINTER": 100}
        )

        # Normalize real_time to be timezone-aware (UTC)
        if real_time.tzinfo is None:
            real_time = real_time.replace(tzinfo=UTC)

        # Calculate elapsed real time
        elapsed = real_time - epoch_start
        elapsed_minutes = elapsed.total_seconds() / 60.0

        # Convert to game time
        game_hours_elapsed = elapsed_minutes * multiplier

        total_game_minutes = int(game_hours_elapsed * 60)
        game_minute = total_game_minutes % 60
        total_game_hours = total_game_minutes // 60
        game_hour = total_game_hours % hours_per_day
        total_game_days = total_game_hours // hours_per_day
        year_day = (total_game_days % days_per_year) + 1
        game_year = (total_game_days // days_per_year) + 1

        # Calculate month and day of month
        months_per_year = game_time.game_time_config.get("months_per_year", 20)
        days_per_month = game_time.game_time_config.get("days_per_month", 20)
        game_month = ((year_day - 1) // days_per_month) + 1
        if game_month > months_per_year:
            game_month = months_per_year
        game_day = ((year_day - 1) % days_per_month) + 1

        # Calculate cycle year (1-12)
        cycle_year = ((game_year - 1) % 12) + 1

        # Calculate season
        season_days = game_time.game_time_config.get(
            "season_days", {"SPRING": 100, "SUMMER": 100, "FALL": 100, "WINTER": 100}
        )
        spring_days = season_days.get("SPRING", 100)
        summer_days = season_days.get("SUMMER", 100)
        fall_days = season_days.get("FALL", 100)

        if year_day <= spring_days:
            season = "SPRING"
        elif year_day <= spring_days + summer_days:
            season = "SUMMER"
        elif year_day <= spring_days + summer_days + fall_days:
            season = "FALL"
        else:
            season = "WINTER"

        return {
            "year": game_year,
            "year_day": year_day,
            "month": game_month,
            "day": game_day,
            "hour": game_hour,
            "minute": game_minute,
            "season": season,
            "cycle_year": cycle_year,
        }

    async def convert_game_to_real_time(
        self, game_year: int, game_day: int, game_hour: int, game_minute: int = 0
    ) -> datetime:
        """
        Convert game time to real datetime.

        Args:
            game_year: Game year
            game_day: Game day (1-based)
            game_hour: Game hour (0-29)
            game_minute: Game minute (0-59)

        Returns:
            Real datetime
        """
        game_time = await self.get_current_game_time()
        settings = await self._get_settings()
        epoch_start = settings.game_epoch_start or game_time.current_game_time
        multiplier = settings.game_time_multiplier

        # Get config values from settings
        hours_per_day = settings.game_hours_per_day
        days_per_year = settings.game_days_per_year

        # Calculate total game time elapsed
        total_game_days = (game_year - 1) * days_per_year + (game_day - 1)
        total_game_hours = total_game_days * hours_per_day + game_hour
        total_game_minutes = total_game_hours * 60 + game_minute

        # Convert to real time
        real_minutes_elapsed = total_game_minutes / multiplier
        # Ensure epoch_start is timezone-aware before arithmetic
        if epoch_start.tzinfo is None:
            epoch_start = epoch_start.replace(tzinfo=UTC)

        real_time = epoch_start + timedelta(minutes=real_minutes_elapsed)

        return real_time

    async def get_season_start(self, season: Season) -> dict:
        """
        Get when the current season started (game time).

        Args:
            season: Season to check

        Returns:
            Game time dict: {year, day, hour}
        """
        game_time = await self.get_current_game_time()
        settings = await self._get_settings()
        # Season days are still in game_time_config (not duplicated in GameSettings)
        season_days = game_time.game_time_config.get(
            "season_days", {"SPRING": 100, "SUMMER": 100, "FALL": 100, "WINTER": 100}
        )

        current_year_day = (
            game_time.year_day
            if hasattr(game_time, "year_day") and game_time.year_day
            else (
                game_time.game_day if hasattr(game_time, "game_day") and game_time.game_day else 1
            )
        )
        current_year = game_time.game_year

        spring_days = season_days.get("SPRING", 100)
        summer_days = season_days.get("SUMMER", 100)
        fall_days = season_days.get("FALL", 100)

        if season == "SPRING":
            season_start_day = 1
        elif season == "SUMMER":
            season_start_day = spring_days + 1
        elif season == "FALL":
            season_start_day = spring_days + summer_days + 1
        else:  # WINTER
            season_start_day = spring_days + summer_days + fall_days + 1

        # Calculate which year and day
        days_per_year = settings.game_days_per_year
        if current_year_day >= season_start_day:
            # Season started this year
            return {"year": current_year, "year_day": season_start_day, "hour": 0}
        # Season started last year
        return {"year": current_year - 1, "year_day": season_start_day, "hour": 0}

    async def fast_forward_on_startup(self) -> GameTime:
        """
        Fast-forward game time based on real-world time elapsed since last shutdown.
        This maintains immersion by advancing game time even when the bot is offline.

        Returns:
            Updated GameTime instance
        """
        game_time = await self.get_current_game_time()
        now = datetime.now(UTC)

        # If we have a last shutdown time, calculate elapsed time
        if game_time.last_shutdown_time:
            # Calculate elapsed real-world time
            elapsed = now - game_time.last_shutdown_time
            elapsed_minutes = elapsed.total_seconds() / 60.0

            if elapsed_minutes > 0:
                self.logger.info(
                    f"Fast-forwarding game time: {elapsed_minutes:.2f} real minutes elapsed "
                    f"(since {game_time.last_shutdown_time.isoformat()})"
                )

                # Advance game time by the elapsed real-world time
                game_time = await self.advance_game_time(real_minutes=elapsed_minutes)

                self.logger.info(
                    f"Game time fast-forwarded to: Year {game_time.game_year}, "
                    f"Day {game_time.year_day}, {game_time.game_hour:02d}:{game_time.game_minute:02d}, "
                    f"{game_time.season}"
                )
            else:
                self.logger.info("No time elapsed since last shutdown, skipping fast-forward")
        else:
            self.logger.info("No previous shutdown time recorded, skipping fast-forward")

        # Update current_game_time to now
        game_time.current_game_time = now

        # Clear last_shutdown_time (will be set again on shutdown)
        game_time.last_shutdown_time = None

        return await self.repository.update_game_time(game_time)

    async def persist_game_time_incremental(self) -> None:
        """
        Persist current game time state incrementally (without updating last_shutdown_time).
        This is called periodically to save state in case of crashes.
        """
        try:
            game_time = await self.get_current_game_time()
            now = datetime.now(UTC)

            # Save current state (but don't update last_shutdown_time - that's only for actual shutdown)
            game_time.current_game_time = now

            await self.repository.update_game_time(game_time)

            self.logger.debug(
                f"Game time persisted incrementally: Year {game_time.game_year}, "
                f"Day {game_time.year_day}, {game_time.game_hour:02d}:{game_time.game_minute:02d}, "
                f"{game_time.season}"
            )
        except Exception as e:
            self.logger.error(f"Failed to persist game time incrementally: {e}", exc_info=True)

    async def persist_game_time_on_shutdown(self) -> None:
        """
        Persist current game time state on bot shutdown.
        This saves the shutdown time so we can fast-forward on next startup.
        """
        try:
            game_time = await self.get_current_game_time()
            now = datetime.now(UTC)

            # Save current state and shutdown time
            game_time.current_game_time = now
            game_time.last_shutdown_time = now

            await self.repository.update_game_time(game_time)

            self.logger.info(
                f"Game time persisted on shutdown: Year {game_time.game_year}, "
                f"Day {game_time.year_day}, {game_time.game_hour:02d}:{game_time.game_minute:02d}, "
                f"{game_time.season} (shutdown at {now.isoformat()})"
            )
        except Exception as e:
            self.logger.error(f"Failed to persist game time on shutdown: {e}", exc_info=True)
