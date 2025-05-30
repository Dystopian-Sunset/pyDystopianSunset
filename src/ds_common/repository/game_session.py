import logging

import discord

from ds_common.models.character import Character
from ds_common.models.game_session import GameSession
from ds_common.models.player import Player
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.surreal_manager import SurrealManager


class GameSessionRepository(BaseRepository[GameSession]):
    def __init__(self, surreal_manager: SurrealManager):
        super().__init__(surreal_manager, GameSession, "game_session")
        self.logger: logging.Logger = logging.getLogger(__name__)

    
    async def from_channel(
        self, channel: discord.TextChannel | discord.VoiceChannel
    ) -> "GameSession | None":
        """
        Returns the game session from the channel.
        """
        query = f'SELECT * FROM {self.table_name} WHERE name == "{channel.name}";'
        self.logger.debug("Query: %s", query)
        async with self.surreal_manager.get_db() as db:
            result = await db.query(query)
        self.logger.debug("Result: %s", result)
        if not result:
            return None

        return GameSession(**result[0])
    
    async def update_last_active_at(
        self, channel: discord.TextChannel | discord.VoiceChannel
    ) -> None:
        query = f'UPDATE {self.table_name} SET last_active = time::now() WHERE channel_id = "{channel.id}";'
        self.logger.debug("Query: %s", query)
        async with self.surreal_manager.get_db() as db:
            await db.query(query)

    async def add_player(self, player: Player, game_session: GameSession) -> None:
        query = f"RELATE {player.id}->player_is_playing_in->{game_session.id}"
        self.logger.debug("Query: %s", query)
        async with self.surreal_manager.get_db() as db:
            await db.query(query)

    async def remove_player(self, player: Player, game_session: GameSession) -> None:
        query = f"DELETE {player.id}-player_is_playing_in-{game_session.id}"
        self.logger.debug("Query: %s", query)
        async with self.surreal_manager.get_db() as db:
            await db.query(query)

        if not await self.players(game_session):
            await self.delete(game_session)
            self.logger.debug("Deleted game empty session %s", game_session)

    async def add_character(
        self, character: Character, game_session: GameSession
    ) -> None:
        query = f"RELATE {character.id}->character_is_playing_in->{game_session.id}"
        self.logger.debug("Query: %s", query)
        async with self.surreal_manager.get_db() as db:
            await db.query(query)

    async def remove_character(
        self, character: Character, game_session: GameSession
    ) -> None:
        query = f"DELETE {character.id}-character_is_playing_in-{game_session.id}"
        self.logger.debug("Query: %s", query)
        async with self.surreal_manager.get_db() as db:
            await db.query(query)

    async def players(self, game_session: GameSession) -> list[Player] | None:
        """
        Returns the players in the game session.
        """
        query = f"SELECT <-player_is_playing_in<-player.* AS players FROM game_session WHERE name == '{game_session.name}';"
        self.logger.debug("Query: %s", query)

        async with self.surreal_manager.get_db() as db:
            result = await db.query(query)
        self.logger.debug("Result: %s", result)

        if not result or not result[0]["players"]:
            self.logger.debug("No players found")
            return []

        self.logger.debug("Players found: %s", result[0]["players"])
        return [Player(**player) for player in result[0]["players"]]

    async def characters(self, game_session: GameSession) -> list[Character] | None:
        """
        Returns the characters in the game session.
        """
        query = f"SELECT <-character_is_playing_in<-character.* AS characters FROM game_session WHERE name == '{game_session.name}';"
        self.logger.debug("Query: %s", query)

        async with self.surreal_manager.get_db() as db:
            result = await db.query(query)
        self.logger.debug("Result: %s", result)

        if not result or not result[0]["characters"]:
            self.logger.debug("No characters found")
            return []

        self.logger.debug("Characters found: %s", result[0]["characters"])
        return [Character(**character) for character in result[0]["characters"]]