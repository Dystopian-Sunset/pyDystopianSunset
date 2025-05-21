import logging

from surrealdb import AsyncSurreal

from ds_common.models.character_class import CharacterClass
from ds_common.models.character_stat import CharacterStat
from ds_common.repository.base_repository import BaseRepository


class CharacterClassRepository(BaseRepository[CharacterClass]):
    def __init__(self, db: AsyncSurreal):
        super().__init__(db, CharacterClass)
        self.table_name = "character_class"
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def get_stats(self, character_class: CharacterClass) -> list[CharacterStat]:
        query = f"""
        SELECT ->has_class_stat->character_stats.* AS stats 
FROM {self.table_name} 
WHERE id = {character_class.id}
"""
        self.logger.debug("Query: %s", query)

        result = await self.db.select(query)
        self.logger.debug("Result: %s", result)

        if not result:
            self.logger.debug("No stats found")
            return []

        self.logger.debug("Stats found: %s", result)
        return [CharacterStat(**stat) for stat in result]