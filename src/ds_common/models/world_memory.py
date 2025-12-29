from typing import Literal
from uuid import UUID

from sqlalchemy import JSON, Column, String
from sqlalchemy.dialects import postgresql
from sqlmodel import Field

from ds_common.models.base_model import BaseSQLModel

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    # Fallback if pgvector is not installed yet
    from sqlalchemy import ARRAY as SQLArray
    from sqlalchemy import Float as SQLFloat

    def Vector(dim: int) -> type[SQLArray[SQLFloat]]:  # noqa: ARG001
        return SQLArray(SQLFloat)


MemoryCategory = Literal["event", "character", "location", "faction"]
ImpactLevel = Literal["minor", "moderate", "major", "world_changing"]


class WorldMemory(BaseSQLModel, table=True):
    """
    World memory model for storing permanent historical record.

    These memories persist forever (or until GM explicitly removes).
    """

    __tablename__ = "world_memories"

    memory_category: str | None = Field(
        default=None, description="Category of world memory"
    )  # MemoryCategory = Literal["event", "character", "location", "faction"]

    title: str | None = Field(default=None, max_length=255, description="Memory title")
    description: str | None = Field(default=None, description="Concise description (50-500 chars)")
    full_narrative: str | None = Field(
        default=None, description="Rich detail narrative (200-3000 chars)"
    )

    related_entities: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Related entities as {characters: [], locations: [], factions: []}",
    )
    source_episodes: "list[UUID]" = Field(  # type: ignore[valid-type]
        default_factory=list,
        sa_column=Column(postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        description="Episode IDs that contributed to this world memory",
    )
    consequences: list[str] = Field(
        default_factory=list,
        sa_column=Column(postgresql.ARRAY(String)),
        description="Consequences or ripple effects",
    )

    embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(768)),
        description="Vector embedding for semantic search (768 dimensions - matches nomic-embed-text)",
    )
    tags: list[str] = Field(
        default_factory=list,
        sa_column=Column(postgresql.ARRAY(String)),
        description="Tags for categorization",
    )
    impact_level: str | None = Field(
        default=None, index=True, description="Impact level of this memory"
    )  # ImpactLevel = Literal["minor", "moderate", "major", "world_changing"]

    # Discovery system
    is_public: bool = Field(
        default=True, index=True, description="Whether this memory is publicly discoverable"
    )
    discovery_requirements: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Requirements for discovering this memory",
    )

    # Extended fields for dynamic world elements
    related_world_event_id: UUID | None = Field(
        default=None, description="Related world event ID if this memory is from an event"
    )
    related_world_item_id: UUID | None = Field(
        default=None, description="Related world item ID if this memory is from an item"
    )
    regional_context: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Regional context: {city, district, sector, factions}",
    )
    game_time_context: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Game time when memory was created: {year, day, hour, season}",
    )
