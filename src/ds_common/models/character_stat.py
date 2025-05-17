from pydantic import BaseModel, ConfigDict, Field
from surrealdb import AsyncSurreal, RecordID


class CharacterStat(BaseModel):
    id: RecordID = Field(primary_key=True)
    name: str
    abbr: str
    description: str
    emoji: str
    max_value: int
    is_primary: bool
    is_mutable: bool

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    async def from_db_select(cls, db: AsyncSurreal, id: int) -> "CharacterStat":
        return cls(**await db.select(RecordID("character_stat", id)))
        