from datetime import datetime
from typing import TYPE_CHECKING, Literal, Optional
from uuid import UUID

from sqlalchemy import JSON, Column, DateTime, Float, String
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, Relationship

from ds_common.models.base_model import BaseSQLModel

if TYPE_CHECKING:
    from ds_common.models.character import Character
    from ds_common.models.game_session import GameSession


MemoryType = Literal["dialogue", "action", "observation"]


class SessionMemory(BaseSQLModel, table=True):
    """
    Session memory model for storing raw events during active gameplay.

    These memories are ephemeral and expire after processing (default 4 hours).
    """

    __tablename__ = "session_memories"

    session_id: UUID = Field(
        foreign_key="game_sessions.id", index=True, description="Game session ID"
    )
    character_id: UUID = Field(foreign_key="characters.id", index=True, description="Character ID")
    timestamp: datetime = Field(
        sa_type=DateTime(timezone=True),
        description="When the event occurred (UTC)",
    )
    memory_type: str | None = Field(
        default=None, description="Type of memory"
    )  # MemoryType = Literal["dialogue", "action", "observation"]
    content: dict = Field(
        sa_column=Column(JSON),
        description="Event content as JSONB",
    )
    participants: "list[UUID]" = Field(  # type: ignore[valid-type]
        default_factory=list,
        sa_column=Column(postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        description="List of participant character/NPC IDs",
    )
    location_id: UUID | None = Field(default=None, description="Location ID if applicable")

    # AI-generated metadata
    importance_score: float | None = Field(
        default=None,
        sa_column=Column(Float),
        description="Importance score from 0.0 to 1.0",
    )
    emotional_valence: float | None = Field(
        default=None,
        sa_column=Column(Float),
        description="Emotional valence from -1.0 to 1.0",
    )
    tags: list[str] = Field(
        default_factory=list,
        sa_column=Column(postgresql.ARRAY(String)),
        description="AI-generated tags",
    )

    expires_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        description="When this memory expires (UTC)",
    )
    processed: bool = Field(
        default=False, index=True, description="Whether this has been processed into an episode"
    )

    # Relationships
    session: Optional["GameSession"] = Relationship()
    character: Optional["Character"] = Relationship()
