from datetime import datetime, timezone

from discord import Member
from sqlmodel import Field, SQLModel
from surrealdb import AsyncSurreal, RecordID

from ds_common.models.character import Character


class Player(SQLModel, table=True):
    id: int = Field(primary_key=True)
    global_name: str
    display_name: str
    display_avatar: str | None
    joined_at: datetime
    last_active: datetime
    is_active: bool

    @classmethod
    def from_member(cls, member: Member, is_active: bool = True) -> "Player":
        return cls(
            id=member.id,
            global_name=member.global_name,
            display_name=member.display_name,
            display_avatar=member.display_avatar.url,
            joined_at=datetime.now(timezone.utc),
            last_active=datetime.now(timezone.utc),
            is_active=is_active,
        )

    @classmethod
    async def from_db(cls, db: AsyncSurreal, id: int | str | RecordID) -> "Player":
        if isinstance(id, int):
            id = RecordID("player", id)
        elif isinstance(id, str) and id.startswith("player:"):
            id = RecordID("player", int(id.split(":")[1]))

        result = await db.select(id)

        if not result:
            return None

        return cls(**result)

    async def upsert(self, db: AsyncSurreal) -> None:
        return await db.upsert(
            RecordID("player", self.id),
            self.model_dump(),
        )

    async def update_last_active(self, db: AsyncSurreal):
        self.last_active = datetime.now(timezone.utc)

        return await db.update(RecordID("player", self.id), self.model_dump())

    async def get_characters(self, db: AsyncSurreal) -> list["Character"]:
        query = f"SELECT ->has_character->(?).* AS characters FROM player:{self.id}"
        result = await db.query(query)

        if not result:
            return []

        return [Character(**character) for character in result[0]["characters"]]

    async def relate_character(self, db: AsyncSurreal, character: "Character") -> None:
        query = f"RELATE player:{self.id}->has_character->character:{character.id}"
        return await db.query(query)

    async def get_active_character(self, db: AsyncSurreal) -> "Character":
        query = (
            f"SELECT ->is_playing_as->(?).* AS character FROM player:{self.id} LIMIT 1"
        )
        result = await db.query(query)

        if not result or not result[0]["character"]:
            return None

        return Character(**result[0]["character"][0])

    async def set_active_character(
        self, db: AsyncSurreal, character: "Character"
    ) -> None:
        await db.delete(f"player:{self.id}->is_playing_as")
        query = f"RELATE player:{self.id}->is_playing_as->character:{character.id}"
        return await db.query(query)


class PlayerHasCharacter(SQLModel, table=True):
    id: int = Field(primary_key=True)
    character_id: int = Field(alias="in", foreign_key="character.id")
    player_id: int = Field(alias="out", foreign_key="player.id")