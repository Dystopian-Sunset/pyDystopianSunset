from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship

from ds_common.models.base_model import BaseSQLModel

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    # Fallback if pgvector is not installed yet
    from sqlalchemy import ARRAY, Float

    def Vector(dim: int) -> type[ARRAY[Float]]:  # noqa: ARG001
        return ARRAY(Float)


if TYPE_CHECKING:
    from ds_common.models.npc import NPC


class NPCMemory(BaseSQLModel, table=True):
    """
    NPC memory model for storing vector embeddings of NPC memories.

    Used for semantic search and context retrieval in AI interactions.
    """

    __tablename__ = "npc_memories"

    npc_id: UUID = Field(foreign_key="npcs.id", index=True, description="NPC ID")
    memory_text: str = Field(description="The memory text content")
    embedding: list[float] = Field(
        sa_column=Column(Vector(768)),
        description="Vector embedding of the memory (768 dimensions - matches nomic-embed-text)",
    )
    meta_data: dict[str, str] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Additional metadata about the memory",
    )

    # Relationships
    npc: Optional["NPC"] = Relationship()
