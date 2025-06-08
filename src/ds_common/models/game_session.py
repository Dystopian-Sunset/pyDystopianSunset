from datetime import datetime, timezone

from pydantic import ConfigDict, Field

from ds_common.models.surreal_model import BaseSurrealModel
from ds_common.name_generator import NameGenerator


class GameSession(BaseSurrealModel):
    """
    Game session model
    """

    name: str = Field(
        default_factory=NameGenerator.generate_cyberpunk_channel_name,
        description="Name of the game session",
    )
    channel_id: int | None = Field(
        default=None,
        description="ID of the channel where the game session is taking place",
    )
    max_players: int = Field(
        default=4, description="Max number of players allowed in the game"
    )
    is_open: bool = Field(
        default=False, description="True if the game is open for all players to join"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the game session was created",
    )
    last_active_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the game session was last active",
    )

    model_config = ConfigDict(table_name="game_session")
