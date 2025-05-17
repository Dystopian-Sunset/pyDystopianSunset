from sqlmodel import Field, SQLModel


class GameSettings(SQLModel, table=True):
    id: int = Field(primary_key=True)
    max_characters_per_player: int = Field(default=1)
