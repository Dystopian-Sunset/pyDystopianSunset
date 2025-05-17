from pydantic import BaseModel, ConfigDict, Field
from surrealdb import RecordID


class GameSettings(BaseModel):
    id: RecordID = Field(primary_key=True, default=RecordID("game_settings", 1))
    max_characters_per_player: int = Field(default=1)

    model_config = ConfigDict(arbitrary_types_allowed=True)
