from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import JSON, Column, DateTime, Float
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, Relationship, UniqueConstraint

from ds_common.models.base_model import BaseSQLModel

if TYPE_CHECKING:
    from ds_common.models.character import Character


class CharacterRecognition(BaseSQLModel, table=True):
    """
    Character recognition model for tracking what each character knows about others.

    Enables realistic NPC dialogue based on past interactions.
    """

    __tablename__ = "character_recognition"
    __table_args__ = (
        UniqueConstraint("character_id", "known_character_id", name="uq_character_known_character"),
    )

    character_id: UUID = Field(
        foreign_key="characters.id", index=True, description="Observer character ID"
    )
    known_character_id: UUID = Field(
        foreign_key="characters.id", index=True, description="Known character ID"
    )

    first_met_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        description="When they first met (UTC)",
    )
    last_interaction_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        description="When they last interacted (UTC)",
    )

    known_name: str | None = Field(
        default=None, max_length=255, description="Name they know this character by"
    )
    known_details: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Known details about this character",
    )
    relationship_type: str | None = Field(
        default=None, max_length=50, description="Type of relationship"
    )
    trust_level: float | None = Field(
        default=None,
        sa_column=Column(Float),
        description="Trust level from 0.0 to 1.0",
    )

    shared_episodes: "list[UUID]" = Field(  # type: ignore[valid-type]
        default_factory=list,
        sa_column=Column(postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        description="Episode IDs where they interacted",
    )

    # Relationships
    character: Optional["Character"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[CharacterRecognition.character_id]"}
    )
    known_character: Optional["Character"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[CharacterRecognition.known_character_id]"}
    )
