import logging

from ds_common.models.character import Character
from ds_common.models.character_class import CharacterClass
from ds_common.models.player import Player
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.surreal_manager import SurrealManager


class CharacterRepository(BaseRepository[Character]):
    def __init__(self, surreal_manager: SurrealManager):
        super().__init__(surreal_manager, Character)
        self.table_name = "character"
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def get_character_class(self, character: Character) -> CharacterClass | None:
        query = f"SELECT ->has_class->(?).* AS character_class FROM {character.id} LIMIT 1"
        self.logger.debug("Query: %s", query)

        async with self.surreal_manager.get_db() as db:
            result = await db.query(query)
        self.logger.debug("Result: %s", result)

        if not result or not result[0]["character_class"]:
            self.logger.debug("Character class not found")
            return None

        self.logger.debug("Character class found: %s", result[0]["character_class"][0])
        return CharacterClass(**result[0]["character_class"][0])

    async def set_character_class(
        self, character: Character, character_class: CharacterClass
    ) -> None:
        query = f"RELATE {character.id}->has_class->{character_class.id}"
        self.logger.debug("Query: %s", query)

        async with self.surreal_manager.get_db() as db:
            await db.query(query)
        self.logger.debug("Character class set: %s", character_class)

    async def get_player(self, character: Character) -> Player | None:
        query = f"SELECT ->player_is_playing_as->(?).* AS player FROM {character.id} LIMIT 1"
        self.logger.debug("Query: %s", query)

        async with self.surreal_manager.get_db() as db:
            result = await db.query(query)
        self.logger.debug("Result: %s", result)

        if not result or not result[0]["player"]:
            self.logger.debug("Player not found")
            return None

        self.logger.debug("Player found: %s", result[0]["player"][0])
        return Player(**result[0]["player"][0])