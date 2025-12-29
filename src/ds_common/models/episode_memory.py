from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Column, DateTime, Float, String
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


class EpisodeMemory(BaseSQLModel, table=True):
    """
    Episode memory model for storing condensed narrative summaries of sessions.

    These memories are short-term (default 48 hours) unless promoted to world memory.
    """

    __tablename__ = "episode_memories"

    expires_at: datetime = Field(
        index=True,
        sa_type=DateTime(timezone=True),
        description="When this episode expires (UTC)",
    )

    # Narrative content
    title: str | None = Field(default=None, max_length=255, description="Episode title")
    summary: str | None = Field(default=None, description="Narrative summary")
    one_sentence_summary: str | None = Field(default=None, description="Quick reference summary")
    key_moments: list[dict] = Field(
        default_factory=list,
        sa_column=Column(postgresql.ARRAY(JSON)),
        description="List of key moments as JSONB",
    )
    relationships_changed: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Relationship changes as JSONB",
    )
    themes: list[str] = Field(
        default_factory=list,
        sa_column=Column(postgresql.ARRAY(String)),
        description="Themes identified in the episode",
    )
    cliffhangers: list[str] = Field(
        default_factory=list,
        sa_column=Column(postgresql.ARRAY(String)),
        description="Cliffhangers or unresolved threads",
    )

    # References
    characters: "list[UUID]" = Field(  # type: ignore[valid-type]
        default_factory=list,
        sa_column=Column(postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        description="Character IDs involved in this episode",
    )
    locations: "list[UUID]" = Field(  # type: ignore[valid-type]
        default_factory=list,
        sa_column=Column(postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        description="Location IDs involved in this episode",
    )
    session_ids: "list[UUID]" = Field(  # type: ignore[valid-type]
        default_factory=list,
        sa_column=Column(postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        description="Session IDs that contributed to this episode",
    )

    # Semantic search
    embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(768)),
        description="Vector embedding for semantic search (768 dimensions - matches nomic-embed-text)",
    )
    importance_score: float | None = Field(
        default=None,
        sa_column=Column(Float),
        description="Overall importance score",
    )
    promoted_to_world: bool = Field(
        default=False, index=True, description="Whether this was promoted to world memory"
    )
