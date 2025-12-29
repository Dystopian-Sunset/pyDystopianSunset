from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from discord import Member, User
from sqlalchemy import BigInteger, DateTime
from sqlmodel import Column, Field, Relationship

from ds_common.models.base_model import BaseSQLModel
from ds_common.models.junction_tables import GameSessionPlayer, PlayerCharacter

if TYPE_CHECKING:
    from ds_common.models.character import Character
    from ds_common.models.game_session import GameSession


class Player(BaseSQLModel, table=True):
    """
    Player model

    A player is a Discord user who is registered in the game.
    """

    __tablename__ = "players"

    discord_id: int = Field(
        sa_column=Column(BigInteger(), unique=True, index=True),
        description="Discord player ID (64-bit integer)",
    )
    global_name: str = Field(description="Discord player global name")
    display_name: str = Field(description="Discord player display name")
    display_avatar: str | None = Field(
        default=None, description="Discord player display avatar URL"
    )
    joined_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        description="Player joined at (UTC)",
    )
    last_active_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        description="Player last active (UTC)",
    )
    is_active: bool = Field(default=True, description="Player is active")
    is_banned: bool = Field(default=False, description="Player is banned")

    # Foreign keys
    active_character_id: UUID | None = Field(default=None, foreign_key="characters.id")

    # Relationships
    characters: list["Character"] = Relationship(
        back_populates="players",
        link_model=PlayerCharacter,
    )
    active_character: Optional["Character"] = Relationship(
        back_populates="active_for_player",
        sa_relationship_kwargs={
            "foreign_keys": "[Player.active_character_id]",
            "primaryjoin": "Player.active_character_id == Character.id",
        },
    )
    game_sessions: list["GameSession"] = Relationship(
        back_populates="players",
        link_model=GameSessionPlayer,
    )

    @classmethod
    def from_member(
        cls, member: Member | User, is_active: bool = True, is_banned: bool = False
    ) -> "Player":
        return cls(
            discord_id=member.id,
            global_name=member.global_name,
            display_name=member.display_name,
            display_avatar=member.display_avatar.url,
            joined_at=datetime.now(UTC),
            last_active_at=datetime.now(UTC),
            is_active=is_active,
            is_banned=is_banned,
        )
