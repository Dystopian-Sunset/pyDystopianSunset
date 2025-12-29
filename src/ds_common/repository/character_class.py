import logging

from sqlalchemy.ext.asyncio import AsyncSession

from ds_common.models.character_class import CharacterClass
from ds_common.models.character_stat import CharacterStat
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class CharacterClassRepository(BaseRepository[CharacterClass]):
    """
    Repository for CharacterClass model with relationship operations.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, CharacterClass)
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def get_stats(
        self, character_class: CharacterClass, session: AsyncSession | None = None
    ) -> list[CharacterStat]:
        """
        Get all stats for a character class.

        Args:
            character_class: CharacterClass instance
            session: Optional database session

        Returns:
            List of CharacterStat instances
        """

        async def _execute(sess: AsyncSession):
            if session:
                await sess.refresh(character_class, ["stats"])
                return character_class.stats or []
            fresh_class = await sess.get(CharacterClass, character_class.id)
            if not fresh_class:
                return []
            await sess.refresh(fresh_class, ["stats"])
            return fresh_class.stats or []

        return await self._with_session(_execute, session)
