import logging

from surrealdb import AsyncSurreal

from ds_common.models.character import Character
from ds_common.models.character_class import CharacterClass
from ds_common.repository.base_repository import BaseRepository


class CharacterRepository(BaseRepository[Character]):
    def __init__(self, db: AsyncSurreal):
        super().__init__(db, Character)
        self.table_name = "character"
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def get_character_class(self, character: Character) -> CharacterClass | None:
        query = f"SELECT ->has_class->(?).* AS character_class FROM {character.id} LIMIT 1"
        self.logger.debug("Query: %s", query)

        result = await self.db.query(query)
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

        await self.db.query(query)
        self.logger.debug("Character class set: %s", character_class)