from pydantic import ConfigDict, Field

from ds_common.models.surreal_model import BaseSurrealModel


class GameSettings(BaseSurrealModel):
    max_characters_per_player: int = Field(default=3)  # max characters per player
    max_game_sessions: int = Field(default=50)  # max game sessions
    max_players_per_game_session: int = Field(default=4)  # max players per game session
    max_game_session_idle_duration: int = Field(default=30)  # in minutes
    game_channel_slowmode_delay: int = Field(default=5)  # in seconds

    model_config = ConfigDict(table_name="game_settings")
