import logging

from ds_common.models.character_stat import CharacterStat
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.surreal_manager import SurrealManager


class CharacterStatRepository(BaseRepository[CharacterStat]):
    def __init__(self, surreal_manager: SurrealManager):
        super().__init__(surreal_manager, CharacterStat, "character_stats")
        self.logger: logging.Logger = logging.getLogger(__name__)