
from pydantic import BaseModel, ConfigDict, Field
from surrealdb import RecordID


class GameSettings(BaseModel):
    id: RecordID = Field(primary_key=True, default=RecordID("game_settings", 1))
    max_characters_per_player: int = Field(default=3)  # max characters per player
    max_game_sessions: int = Field(default=50)  # max game sessions
    max_players_per_game_session: int = Field(default=4)  # max players per game session
    max_game_session_idle_duration: int = Field(default=30)  # in minutes
    game_channel_slowmode_delay: int = Field(default=5)  # in seconds

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __str__(self) -> str:
        return f"GameSettings(id={self.id}, max_characters_per_player={self.max_characters_per_player}, max_game_sessions={self.max_game_sessions}, max_players_per_game_session={self.max_players_per_game_session}, max_game_session_idle_duration={self.max_game_session_idle_duration})"

    def __repr__(self) -> str:
        return self.__str__()