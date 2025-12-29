from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import ARRAY, JSON, Column, DateTime, String
from sqlalchemy.dialects import postgresql
from sqlmodel import Field

from ds_common.models.base_model import BaseSQLModel

# Type aliases for type checking (not used in SQLModel fields)
EventType = Literal["LONG_RUNNING", "CALENDAR", "TRIGGERED", "RECURRING"]
EventStatus = Literal["PLANNED", "ACTIVE", "PAUSED", "COMPLETED", "CANCELLED"]
ImpactLevel = Literal["minor", "moderate", "major", "world_changing"]


class WorldEvent(BaseSQLModel, table=True):
    """
    World event model for tracking dynamic world events.

    Events can be long-running (strikes, conflicts), calendar-based,
    triggered by conditions, or recurring.
    """

    __tablename__ = "world_events"

    event_type: str = Field(
        description="Type of event"
    )  # EventType = Literal["LONG_RUNNING", "CALENDAR", "TRIGGERED", "RECURRING"]
    title: str = Field(max_length=255, description="Event name")
    description: str | None = Field(default=None, description="Event description")
    status: str = Field(
        default="PLANNED", description="Current event status"
    )  # EventStatus = Literal["PLANNED", "ACTIVE", "PAUSED", "COMPLETED", "CANCELLED"]

    # Conditions
    start_conditions: dict | None = Field(
        default=None, sa_column=Column(JSON), description="Conditions for event to start"
    )
    end_conditions: dict | None = Field(
        default=None, sa_column=Column(JSON), description="Conditions for event to end"
    )

    # Timing (real time OR game time)
    start_time: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        description="Real time start (optional, UTC)",
    )
    end_time: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        description="Real time end (optional, UTC)",
    )
    start_game_time: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Game time start: {year, day, hour} (optional)",
    )
    end_game_time: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Game time end: {year, day, hour} (optional)",
    )

    # Recurrence
    recurrence_pattern: dict | None = Field(
        default=None, sa_column=Column(JSON), description="Recurrence pattern if recurring"
    )

    # Regional scope
    regional_scope: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Regional scope: {locations: [], factions: [], districts: []}",
    )

    # Related entities
    related_world_memories: list[UUID] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(postgresql.UUID(as_uuid=True))),
        description="World memory IDs related to this event",
    )
    impact_level: str | None = Field(
        default=None, description="Impact level of this event"
    )  # ImpactLevel = Literal["minor", "moderate", "major", "world_changing"]

    # Metadata
    created_by: str | None = Field(
        default=None, description="Discord user ID who created this event"
    )
    affected_factions: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String)),
        description="Factions affected by this event",
    )
