import asyncio

from pydantic import BaseModel, ConfigDict, Field
from surrealdb import AsyncSurreal, RecordID

from ds_common.models.character_stat import CharacterStat


class CharacterClass(BaseModel):
    id: RecordID = Field(primary_key=True)
    name: str
    description: str
    emoji: str

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    async def from_db(cls, db: AsyncSurreal, id: str | RecordID) -> "CharacterClass":
        if isinstance(id, str) and id.startswith("character_class:"):
            id = RecordID("character_class", int(id.split(":")[1]))

        result = await db.select(id)

        if not result:
            return None

        return cls(**result)

    @classmethod
    async def get_all(cls, db: AsyncSurreal) -> list["CharacterClass"]:
        return [cls(**record) for record in await db.select("character_class")]

    @property
    def character_class_stats(self) -> list[CharacterStat]:
        query = f"SELECT character_class:{self.id}->has_class_stat AS stats FROM character_stats"
        return [CharacterStat(**stat) for stat in asyncio.run(self.db.select(query))]
