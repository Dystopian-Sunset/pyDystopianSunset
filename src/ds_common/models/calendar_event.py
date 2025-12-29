from typing import Literal
from uuid import UUID

from sqlalchemy import ARRAY, JSON, Column, String
from sqlalchemy.dialects import postgresql
from sqlmodel import Field

from ds_common.models.base_model import BaseSQLModel

# Type alias for type checking (not used in SQLModel fields)
CalendarEventType = Literal["HOLIDAY", "FESTIVAL", "OBSERVANCE", "FACTION_CELEBRATION", "CUSTOM"]


class CalendarEvent(BaseSQLModel, table=True):
    """
    Calendar event model for recurring events like holidays and festivals.

    Uses game time system for scheduling and activation.
    """

    __tablename__ = "calendar_events"

    name: str = Field(max_length=255, description="Event name")
    event_type: str = Field(
        description="Type of calendar event"
    )  # CalendarEventType = Literal["HOLIDAY", "FESTIVAL", "OBSERVANCE", "FACTION_CELEBRATION", "CUSTOM"]
    description: str | None = Field(default=None, description="Event description")

    # Game time scheduling
    start_game_time: dict = Field(
        sa_column=Column(JSON),
        description="Game time start: {year, day, hour} (year can be null for recurring)",
    )
    end_game_time: dict = Field(
        sa_column=Column(JSON),
        description="Game time end: {year, day, hour} (year can be null for recurring)",
    )

    # Recurrence
    recurrence: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Recurrence pattern: {pattern: 'yearly'|'monthly'|'custom', ...}",
    )
    is_recurring: bool = Field(default=True, description="Whether this event recurs")

    # Regional variations
    regional_variations: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Regional variations: {region_id: {name, description, ...}}",
    )

    # Faction-specific
    faction_specific: bool = Field(default=False, description="Whether this is faction-specific")
    affected_factions: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String)),
        description="Factions that celebrate this event",
    )

    # Seasonal
    seasonal: bool = Field(default=False, description="Whether this event is tied to seasons")

    # Related entities
    related_world_memories: list[UUID] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(postgresql.UUID(as_uuid=True))),
        description="World memory IDs related to this calendar event",
    )
