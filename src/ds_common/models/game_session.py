from datetime import datetime, timezone

from pydantic import Field
from surrealdb import RecordID

from ds_common.models.character import Character
from ds_common.models.surreal_model import BaseSurrealModel
from ds_common.name_generator import NameGenerator


class GameSession(BaseSurrealModel):
    id: RecordID = Field(
        primary_key=True,
        default_factory=lambda: BaseSurrealModel.create_id("game_session"),
    )
    name: str = Field(
        default_factory=NameGenerator.generate_cyberpunk_channel_name
    )  # Name of the game
    channel_id: int  # ID of the channel where the game session is taking place
    max_players: int = Field(default=4)  # Max number of players allowed in the game
    is_open: bool = Field(default=False)  # True if the game is open for players to join
    players: dict[RecordID, Character] = Field(
        default_factory=dict
    )  # List of players in the game
    created_at: Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )  # When the game session was created
    last_active_at: Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )  # When the game session was last active