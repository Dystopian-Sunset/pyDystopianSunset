from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlmodel import Field

from ds_common.models.base_model import BaseSQLModel


class GameSettings(BaseSQLModel, table=True):
    """
    Game settings model
    """

    __tablename__ = "game_settings"

    max_characters_per_player: int = Field(default=3, description="Max characters per player")
    max_game_sessions: int = Field(default=50, description="Max game sessions")
    max_players_per_game_session: int = Field(default=4, description="Max players per game session")
    max_game_session_idle_duration: int = Field(
        default=30, description="Max game session idle duration in minutes"
    )
    game_channel_slowmode_delay: int = Field(
        default=5, description="Game channel slowmode delay in seconds"
    )

    # Game time settings
    game_time_enabled: bool = Field(default=True, description="Whether game time system is enabled")
    game_time_multiplier: float = Field(
        default=0.5,
        description="How fast game time advances (1 real minute = X game hours). Default 0.5 = 1 real hour = 1 game day",
    )
    game_hours_per_day: int = Field(default=30, description="Hours per game day")
    game_days_per_year: int = Field(default=400, description="Days per game year")
    game_day_start_hour: int = Field(default=0, description="Hour when day begins")
    game_night_start_hour: int = Field(default=15, description="Hour when night begins")
    game_epoch_start: datetime | None = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
        description="When game time epoch started (UTC)",
    )
    game_time_persistence_interval_minutes: int = Field(
        default=5,
        description="Interval in minutes for periodic game time persistence (0 to disable)",
        ge=0,
    )

    # Character stat generation settings
    character_stats_pool_min: int = Field(
        default=60, description="Minimum total stat pool for character generation"
    )
    character_stats_pool_max: int = Field(
        default=80, description="Maximum total stat pool for character generation"
    )
    character_stats_primary_weight: float = Field(
        default=2.5, description="Weight multiplier for primary (class) stats"
    )
    character_stats_secondary_weight: float = Field(
        default=1.0, description="Weight multiplier for secondary (non-class) stats"
    )
    character_stats_luck_min: int = Field(default=1, description="Minimum luck stat value")
    character_stats_luck_max: int = Field(default=10, description="Maximum luck stat value")
    character_stats_stat_min: int = Field(default=1, description="Minimum value for any stat")
    character_stats_stat_max: int = Field(default=20, description="Maximum value for any stat")
    character_stats_allocation_variance: int = Field(
        default=2, description="Variance in point allocation (±variance points)"
    )
    character_stats_max_rerolls: int = Field(
        default=5, description="Maximum number of stat re-rolls allowed during character creation"
    )

    # Memory compression settings
    memory_max_memories: int = Field(
        default=12, description="Maximum number of memories to include in compressed context"
    )
    memory_max_recent_memories: int = Field(
        default=8, description="Maximum number of recent memories to keep detailed (not compressed)"
    )
    memory_importance_threshold: float = Field(
        default=0.3, description="Minimum importance score (0.0-1.0) for filtering memories"
    )
    memory_recent_cutoff_minutes: int = Field(
        default=30, description="Minutes back to consider memories as 'recent' (kept detailed)"
    )
    memory_description_truncate_length: int = Field(
        default=400, description="Maximum length for memory descriptions before truncation"
    )
    memory_environmental_items_lookback_minutes: int = Field(
        default=30, description="Minutes back to look for environmental items in GM responses"
    )
