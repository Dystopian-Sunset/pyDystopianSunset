from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field

from ds_common.models.base_model import BaseSQLModel

# Type aliases for type checking (not used in SQLModel fields)
Season = Literal["SPRING", "SUMMER", "FALL", "WINTER"]
DayOfWeek = Literal["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]


class GameTime(BaseSQLModel, table=True):
    """
    Game time model - singleton table for tracking current game world time.

    Only one record should exist in this table.
    """

    __tablename__ = "game_time"

    # Current game time fields
    current_game_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
        description="Current game world time (real datetime, UTC)",
    )
    game_year: int = Field(default=1, description="Current game year")
    year_day: int = Field(default=1, description="Day of year (1-400, 1-based)")
    game_month: int | None = Field(default=None, description="Current month (1-18)")
    game_day: int | None = Field(default=None, description="Day of month (1-22/23, 1-based)")
    cycle_year: int | None = Field(default=None, description="Year in the 12-year cycle (1-12)")
    game_hour: int = Field(default=0, description="Hour of day (0-29 for 30-hour days)")
    game_minute: int = Field(default=0, description="Minute of hour (0-59)")
    season: str | None = Field(default="SPRING", description="Current season")
    day_of_week: str | None = Field(default="MONDAY", description="Day of week")
    is_daytime: bool = Field(default=True, description="Whether it's currently daytime")

    # Note: time_multiplier and epoch_start have been moved to GameSettings
    # to avoid duplication. Use GameSettings.game_time_multiplier and GameSettings.game_epoch_start

    last_shutdown_time: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        description="When the bot last shut down (UTC), used for fast-forward on startup",
    )

    # Game time configuration (stored as JSON for flexibility)
    # Note: hours_per_day, days_per_year are now in GameSettings
    # game_day_start_hour and game_night_start_hour in GameSettings are base defaults
    # This config stores seasonal variations for day/night times
    game_time_config: dict = Field(
        default_factory=lambda: {
            "months_per_year": 20,
            "days_per_month": 20,  # Average (18-19 for regular, 27 for peak months)
            "season_days": {"SPRING": 100, "SUMMER": 100, "FALL": 100, "WINTER": 100},
            "seasonal_day_night": {
                "SPRING": {"day_start": 0, "night_start": 15},
                "SUMMER": {"day_start": 0, "night_start": 18},  # Longer days in summer
                "FALL": {"day_start": 0, "night_start": 15},
                "WINTER": {"day_start": 0, "night_start": 12},  # Shorter days in winter
            },
        },
        sa_column=Column(JSON),
        description="Game time configuration (non-duplicated fields only)",
    )
