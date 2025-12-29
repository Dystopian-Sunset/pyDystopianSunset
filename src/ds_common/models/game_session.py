from typing import TYPE_CHECKING

from sqlalchemy import BigInteger
from sqlmodel import Column, Field, Relationship

from ds_common.models.base_model import BaseSQLModel
from ds_common.models.junction_tables import (
    GameSessionCharacter,
    GameSessionPlayer,
)
from ds_common.name_generator import NameGenerator

if TYPE_CHECKING:
    from ds_common.models.character import Character
    from ds_common.models.player import Player


class GameSession(BaseSQLModel, table=True):
    """
    Game session model
    """

    __tablename__ = "game_sessions"

    name: str = Field(
        default_factory=NameGenerator.generate_cyberpunk_channel_name,
        description="Name of the game session",
    )
    channel_id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger()),
        description="ID of the Discord channel where the game session is taking place (64-bit integer)",
    )
    max_players: int = Field(default=4, description="Max number of players allowed in the game")
    is_open: bool = Field(
        default=False, description="True if the game is open for all players to join"
    )

    # Relationships
    players: list["Player"] = Relationship(
        back_populates="game_sessions",
        link_model=GameSessionPlayer,
    )
    characters: list["Character"] = Relationship(
        back_populates="game_sessions",
        link_model=GameSessionCharacter,
    )
