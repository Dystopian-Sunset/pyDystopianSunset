import logging

from ds_common.models.character_stat import CharacterStat
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class CharacterStatRepository(BaseRepository[CharacterStat]):
    """
    Repository for CharacterStat model.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, CharacterStat)
        self.logger: logging.Logger = logging.getLogger(__name__)
