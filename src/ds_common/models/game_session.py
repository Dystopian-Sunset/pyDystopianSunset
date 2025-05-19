import random
import string
from datetime import datetime

import discord
from pydantic import BaseModel, ConfigDict, Field
from surrealdb import AsyncSurreal, RecordID

from ds_common.models.player import Player


class GameSession(BaseModel):
    id: RecordID = Field(
        primary_key=True,
        default_factory=lambda: RecordID(
            "game_session",
            "".join(random.choices(string.ascii_letters + string.digits, k=20)),
        ),
    )
    name: str
    channel_id: int
    created_at: datetime
    last_active_at: datetime

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    async def from_db(cls, db: AsyncSurreal, id: str | RecordID) -> "GameSession":
        """
        Returns the game session from the database.
        """
        if isinstance(id, str) and id.startswith("game_session:"):
            id = RecordID("game_session", int(id.split(":")[1]))

        return cls(**await db.select(id))

    @classmethod
    async def get_all(cls, db: AsyncSurreal) -> list["GameSession"]:
        return [cls(**record) for record in await db.select("game_session")]

    @classmethod
    async def from_channel(
        cls, db: AsyncSurreal, channel: discord.TextChannel | discord.VoiceChannel
    ) -> "GameSession | None":
        """
        Returns the game session from the channel.
        """
        query = f'SELECT * FROM game_session WHERE name == "{channel.name}";'
        print(query)
        result = await db.query(query)
        if not result:
            return None

        return cls(**result[0])

    @classmethod
    async def update_last_active_at(
        cls, db: AsyncSurreal, channel: discord.TextChannel | discord.VoiceChannel
    ) -> None:
        query = f'UPDATE game_session SET last_active = time::now() WHERE channel_id = "{channel.id}";'
        await db.query(query)

    async def insert(self, db: AsyncSurreal) -> None:
        """
        Inserts the game session into the database.
        """
        await db.insert(
            "game_session",
            self.model_dump(),
        )

    async def delete(self, db: AsyncSurreal) -> None:
        """
        Deletes the game session from the database.
        """
        try:
            await db.delete(self.id)
        except Exception as e:
            print(e)

    async def update(self, db: AsyncSurreal) -> None:
        """
        Updates the game session in the database.
        """
        await db.update(
            self.id,
            self.model_dump(),
        )

    async def add_player(self, db: AsyncSurreal, player: Player) -> None:
        query = f"RELATE {player.id}->is_playing_in->{self.id}"
        print(query)
        await db.query(query)

    async def remove_player(self, db: AsyncSurreal, player: Player) -> None:
        query = f"DELETE {player.id}-is_playing_in-{self.id}"
        print(query)
        await db.query(query)

    async def players(self, db: AsyncSurreal) -> list[Player] | None:
        """
        Returns the players in the game session.
        """
        query = f"SELECT <-is_playing_in<-player.* AS players FROM game_session WHERE name == '{self.name}';"
        print(query)
        result = await db.query(query)
        if not result or not result[0]["players"]:
            return []
        return [Player(**player) for player in result[0]["players"]]

    @classmethod
    async def is_playing_in(cls, db: AsyncSurreal, player: Player) -> "GameSession | None":
        """
        Returns the game session the player is playing in.
        """
        query = f"SELECT ->is_playing_in->game_session.* AS game_sessions FROM player WHERE id == {player.id};"
        print(query)
        result = await db.query(query)
        if not result or not result[0]["game_sessions"]:
            return None
        return cls(**result[0]["game_sessions"][0])