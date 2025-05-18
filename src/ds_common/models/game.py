
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field
from surrealdb import RecordID

from ds_common.models.character import Character
from ds_common.name_generator import NameGenerator


class Game(BaseModel):
    id: RecordID = Field(primary_key=True, default=RecordID("game", 1))
    name: str = Field(default_factory=NameGenerator.generate_cyberpunk_channel_name) # Name of the game
    max_players: int = Field(default=4) # Max number of players allowed in the game
    is_open: bool = Field(default=False) # True if the game is open for players to join
    players: dict[RecordID, Character] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __str__(self) -> str:
        return f"Game(id={self.id}, name={self.name}, players={self.players}, created_at={self.created_at}, updated_at={self.updated_at})"

    def __repr__(self) -> str:
        return self.__str__()