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
    from ds_common.models.game_session import GameSession


class GameHistoryEmbedding(BaseSQLModel, table=True):
    """
    Game history embedding model for storing vector embeddings of game history.

    Used for semantic search and context retrieval in AI interactions.
    """

    __tablename__ = "game_history_embeddings"

    game_session_id: UUID = Field(
        foreign_key="game_sessions.id", index=True, description="Game session ID"
    )
    history_text: str = Field(description="The history text content")
    embedding: list[float] = Field(
        sa_column=Column(Vector(768)),
        description="Vector embedding of the history (768 dimensions - matches nomic-embed-text)",
    )
    meta_data: dict[str, str] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Additional metadata about the history entry",
    )

    # Relationships
    game_session: Optional["GameSession"] = Relationship()
