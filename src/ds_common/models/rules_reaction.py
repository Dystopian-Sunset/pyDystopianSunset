from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, UniqueConstraint
from sqlmodel import Column, Field, Relationship

from ds_common.models.base_model import BaseSQLModel

if TYPE_CHECKING:
    from ds_common.models.player import Player


class PlayerRulesReaction(BaseSQLModel, table=True):
    """
    Tracks which players have reacted to which rules messages.

    Stores the Discord message ID directly (configured via TOML config).
    """

    __tablename__ = "player_rules_reactions"
    __table_args__ = (UniqueConstraint("player_id", "message_id", name="uq_player_rules_reaction"),)

    player_id: UUID = Field(
        foreign_key="players.id",
        index=True,
        description="Player who reacted",
    )
    message_id: int = Field(
        sa_column=Column(BigInteger(), nullable=False, index=True),
        description="Discord message ID that was reacted to (64-bit integer)",
    )
    reacted_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        default_factory=lambda: datetime.now(UTC),
        description="When the player reacted (UTC)",
    )

    # Relationships
    player: "Player" = Relationship()
