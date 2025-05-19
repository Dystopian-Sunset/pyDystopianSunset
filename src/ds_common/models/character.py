import random
import string
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field
from surrealdb import AsyncSurreal, RecordID

from ds_common.models.character_class import CharacterClass


class Character(BaseModel):
    id: RecordID = Field(
        primary_key=True,
        default_factory=lambda: RecordID(
            "character",
            "".join(random.choices(string.ascii_letters + string.digits, k=20)),
        ),
    )
    name: str
    level: int
    exp: int
    stats: dict[str, int]
    effects: dict[str, int]
    renown: int
    shadow_level: int
    created_at: datetime
    last_active: datetime

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @staticmethod
    async def generate_character(
        name: str,
    ) -> "Character":
        return Character(
            name=name,
            level=1,
            exp=0,
            stats={
                "CHA": random.randint(1, 20),
                "DEX": random.randint(1, 20),
                "INT": random.randint(1, 20),
                "LUK": random.randint(1, 20),
                "PER": random.randint(1, 20),
                "STR": random.randint(1, 20),
            },
            effects={},
            renown=0,
            shadow_level=0,
            created_at=datetime.now(timezone.utc),
            last_active=datetime.now(timezone.utc),
        )

    @classmethod
    async def from_db(cls, db: AsyncSurreal, id: str | RecordID) -> "Character":
        if isinstance(id, str) and id.startswith("character:"):
            id = RecordID("character", int(id.split(":")[1]))

        return cls(**await db.select(id))

    async def insert(self, db: AsyncSurreal) -> None:
        await db.insert(
            "character",
            self.model_dump(),
        )

    async def delete(self, db: AsyncSurreal) -> None:
        try:
            await db.delete(self.id)
        except Exception as e:
            print(e)

    async def update(self, db: AsyncSurreal) -> None:
        await db.update(
            self.id,
            self.model_dump(),
        )

    async def character_class(self, db: AsyncSurreal) -> CharacterClass | None:
        query = f"SELECT ->has_class->(?).* AS character_class FROM {self.id} LIMIT 1"
        result = await db.query(query)
        if not result or not result[0]["character_class"]:
            return None
        return CharacterClass(**result[0]["character_class"][0])

    async def set_class(
        self, db: AsyncSurreal, character_class: CharacterClass
    ) -> None:
        query = f"RELATE {self.id}->has_class->{character_class.id}"
        await db.query(query)
