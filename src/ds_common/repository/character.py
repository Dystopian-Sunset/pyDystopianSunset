import logging

from ds_common.models.character import Character
from ds_common.models.character_class import CharacterClass
from ds_common.models.game_session import GameSession
from ds_common.models.player import Player
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.surreal_manager import SurrealManager


class CharacterRepository(BaseRepository[Character]):
    def __init__(self, surreal_manager: SurrealManager):
        super().__init__(surreal_manager, Character, "character")
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def get_character_class(self, character: Character) -> CharacterClass | None:
        query = (
            f"SELECT ->has_class->(?).* AS character_class FROM {character.id} LIMIT 1"
        )
        self.logger.debug(f"Query: {query}")

        async with self.surreal_manager.get_db() as db:
            result = await db.query(query)
        self.logger.debug(f"Result: {result}")

        if not result or not result[0]["character_class"]:
            self.logger.debug("Character class not found")
            return None

        self.logger.debug(f"Character class found: {result[0]['character_class'][0]}")
        return CharacterClass(**result[0]["character_class"][0])

    async def set_character_class(
        self, character: Character, character_class: CharacterClass
    ) -> None:
        query = f"RELATE {character.id}->has_class->{character_class.id}"
        self.logger.debug(f"Query: {query}")

        async with self.surreal_manager.get_db() as db:
            await db.query(query)
        self.logger.debug(f"Character class set: {character_class}")

    async def get_player(self, character: Character) -> Player | None:
        query = f"SELECT ->player_is_playing_as->(?).* AS player FROM {character.id} LIMIT 1"
        self.logger.debug(f"Query: {query}")

        async with self.surreal_manager.get_db() as db:
            result = await db.query(query)
        self.logger.debug(f"Result: {result}")

        if not result or not result[0]["player"]:
            self.logger.debug("Player not found")
            return None

        self.logger.debug(f"Player found: {result[0]['player'][0]}")
        return Player(**result[0]["player"][0])

    async def get_game_session(self, character: Character) -> GameSession | None:
        query = f"SELECT ->game_session_is_playing_in->(?).* AS game_session FROM {character.id} LIMIT 1"
        self.logger.debug(f"Query: {query}")

        async with self.surreal_manager.get_db() as db:
            result = await db.query(query)
        self.logger.debug(f"Result: {result}")

        if not result or not result[0]["game_session"]:
            self.logger.debug("Game session not found")
            return None

        self.logger.debug(f"Game session found: {result[0]['game_session'][0]}")
        return GameSession(**result[0]["game_session"][0])
