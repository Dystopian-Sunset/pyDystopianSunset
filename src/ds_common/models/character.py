import random
import string
from datetime import datetime

from sqlmodel import Field, SQLModel
from surrealdb import AsyncSurreal, RecordID

from ds_common.models.character_class import CharacterClass


class Character(SQLModel, table=True):
    id: str = Field(
        primary_key=True,
        default_factory=lambda: "".join(
            random.choices(string.ascii_letters + string.digits, k=20)
        ),
    )
    name: str
    created_at: datetime
    last_active: datetime

    @classmethod
    async def from_db(cls, db: AsyncSurreal, id: int | str | RecordID) -> "Character":
        if isinstance(id, int):
            return cls(**await db.select(RecordID("character", id)))
        elif isinstance(id, str) or isinstance(id, RecordID):
            return cls(**await db.select(id))

    async def insert(self, db: AsyncSurreal) -> None:
        await db.insert(
            "character",
            self.model_dump(),
        )

    async def update(self, db: AsyncSurreal) -> None:
        await db.update(
            RecordID("character", self.id),
            self.model_dump(),
        )

    async def character_class(self) -> CharacterClass:
        query = f"SELECT ->has_class->(?).* AS character_class FROM character:{self.id} LIMIT 1"
        result = await self.db.query(query)
        if not result:
            return None
        return CharacterClass(**result[0]["character_class"])

    async def set_class(
        self, db: AsyncSurreal, character_class: CharacterClass
    ) -> None:
        query = f"RELATE character:{self.id}->has_class->{character_class.id}"
        await db.query(query)
