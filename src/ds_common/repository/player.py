import logging

from ds_common.models.character import Character
from ds_common.models.game_session import GameSession
from ds_common.models.player import Player
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.surreal_manager import SurrealManager


class PlayerRepository(BaseRepository[Player]):
    def __init__(self, surreal_manager: SurrealManager):
        super().__init__(surreal_manager, Player, "player")
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def get_by_discord_id(self, discord_id: int) -> Player | None:
        return await self.get_by_("discord_id", discord_id)

    async def get_characters(self, player: Player) -> list["Character"]:
        query = f"SELECT ->player_has_character->(?).* AS characters FROM {player.id};"
        self.logger.debug(f"Query: {query}")

        async with self.surreal_manager.get_db() as db:
            result = await db.query(query)
        self.logger.debug(f"Result: {result}")

        if not result or not result[0]["characters"]:
            self.logger.debug("No characters found")
            return []

        self.logger.debug("Characters found: %s", result[0]["characters"])
        return [Character(**character) for character in result[0]["characters"]]

    async def add_character(self, player: Player, character: "Character") -> None:
        query = f"RELATE {player.id}->player_has_character->{character.id};"
        self.logger.debug(f"Query: {query}")

        async with self.surreal_manager.get_db() as db:
            await db.query(query)
        self.logger.debug(f"Character added: {character} to player: {player}")

    async def remove_character(self, player: Player, character: "Character") -> None:
        async with self.surreal_manager.get_db() as db:
            await db.delete(f"{player.id}->player_has_character->{character.id}")
        self.logger.debug("Deleted character: %s from player: %s", character, player)

    async def get_active_character(self, player: Player) -> "Character | None":
        query = f"SELECT ->player_is_playing_as->(?).* AS character FROM {player.id};"
        self.logger.debug(f"Query: {query}")

        async with self.surreal_manager.get_db() as db:
            result = await db.query(query)
        self.logger.debug(f"Result: {result}")

        if not result or not result[0]["character"]:
            self.logger.debug("No active character found")
            return None

        self.logger.debug(f"Active character found: {result[0]['character'][0]}")
        return Character(**result[0]["character"][0])

    async def set_active_character(
        self, player: Player, character: "Character"
    ) -> None:
        async with self.surreal_manager.get_db() as db:
            await db.delete(f"{player.id}->player_is_playing_as")
        self.logger.debug("Deleted active player_is_playing_as relationship")

        query = f"RELATE {player.id}->player_is_playing_as->{character.id};"
        self.logger.debug(f"Query: {query}")

        async with self.surreal_manager.get_db() as db:
            await db.query(query)
        self.logger.debug(f"Active character set: {character} for player: {player}")

    async def get_game_session(self, player: Player) -> "GameSession | None":
        """
        Returns the game session the player is playing in.
        """
        query = f"SELECT ->player_is_playing_in->game_session.* AS game_sessions FROM player WHERE id == {player.id};"
        self.logger.debug(f"Query: {query}")

        async with self.surreal_manager.get_db() as db:
            result = await db.query(query)
        self.logger.debug(f"Result: {result}")

        if not result or not result[0]["game_sessions"]:
            self.logger.debug("No game session found")
            return None

        self.logger.debug(
            f"Game session found: {result[0]['game_sessions'][0]} for player: {player}"
        )
        return GameSession(**result[0]["game_sessions"][0])
