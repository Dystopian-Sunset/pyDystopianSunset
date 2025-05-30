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

    async def get_characters(self, player: Player) -> list["Character"]:
        query = f"SELECT ->player_has_character->(?).* AS characters FROM {player.id};"
        self.logger.debug("Query: %s", query)

        async with self.surreal_manager.get_db() as db:
            result = await db.query(query)
        self.logger.debug("Result: %s", result)

        if not result or not result[0]["characters"]:
            self.logger.debug("No characters found")
            return []

        self.logger.debug("Characters found: %s", result[0]["characters"])
        return [Character(**character) for character in result[0]["characters"]]

    async def add_character(
        self, player: Player, character: "Character"
    ) -> None:
        query = f"RELATE {player.id}->player_has_character->{character.id};"
        self.logger.debug("Query: %s", query)

        async with self.surreal_manager.get_db() as db:
            await db.query(query)
        self.logger.debug("Active character set: %s", character)

    async def remove_character(
        self, player: Player, character: "Character"
    ) -> None:
        async with self.surreal_manager.get_db() as db:
            await db.delete(f"{player.id}->player_has_character->{character.id}")
        self.logger.debug("Deleted character: %s", character)

    async def get_active_character(self, player: Player) -> "Character | None":
        query = f"SELECT ->player_is_playing_as->(?).* AS character FROM {player.id};"
        self.logger.debug("Query: %s", query)

        async with self.surreal_manager.get_db() as db:
            result = await db.query(query)
        self.logger.debug("Result: %s", result)

        if not result or not result[0]["character"]:
            self.logger.debug("No active character found")
            return None

        self.logger.debug("Active character found: %s", result[0]["character"][0])
        return Character(**result[0]["character"][0])

    async def set_active_character(
        self, player: Player, character: "Character"
    ) -> None:
        async with self.surreal_manager.get_db() as db:
            await db.delete(f"{player.id}->player_is_playing_as")
        self.logger.debug("Deleted active player_is_playing_as relationship")

        query = f"RELATE {player.id}->player_is_playing_as->{character.id};"
        self.logger.debug("Query: %s", query)

        async with self.surreal_manager.get_db() as db:
            await db.query(query)
        self.logger.debug("Active character set: %s", character)

    async def get_game_session(
        self, player: Player
    ) -> "GameSession | None":
        """
        Returns the game session the player is playing in.
        """
        query = f"SELECT ->player_is_playing_in->game_session.* AS game_sessions FROM player WHERE id == {player.id};"
        self.logger.debug("Query: %s", query)

        async with self.surreal_manager.get_db() as db:
            result = await db.query(query)
        self.logger.debug("Result: %s", result)

        if not result or not result[0]["game_sessions"]:
            self.logger.debug("No game session found")
            return None

        self.logger.debug("Game session found: %s", result[0]["game_sessions"][0])
        return GameSession(**result[0]["game_sessions"][0])