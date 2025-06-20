import logging

from ds_common.models.character import Character
from ds_common.models.quest import Quest
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.surreal_manager import SurrealManager


class QuestRepository(BaseRepository[Quest]):
    def __init__(self, surreal_manager: SurrealManager):
        super().__init__(surreal_manager, Quest, "quest")
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def get_character_quests(self, character: Character) -> list[Quest] | None:
        query = (
            f"SELECT ->has_quest->(?).* AS character_quests FROM {character.id} LIMIT 1"
        )
        self.logger.debug(f"Query: {query}")

        async with self.surreal_manager.get_db() as db:
            result = await db.query(query)
        self.logger.debug(f"Result: {result}")

        if not result or not result[0]["character_quests"]:
            self.logger.debug("Character quests not found")
            return None

        self.logger.debug(f"Character quests found: {result[0]['character_quests']}")
        return [Quest(**quest) for quest in result[0]["character_quests"]]

    async def add_character_quest(self, character: Character, quest: Quest) -> None:
        query = f"RELATE {character.id}->has_quest->{quest.id}"
        self.logger.debug(f"Query: {query}")

        async with self.surreal_manager.get_db() as db:
            await db.query(query)
        self.logger.debug(f"Character quest added: {quest}")
