import logging

from surrealdb import AsyncSurreal

from ds_common.models.character_stat import CharacterStat
from ds_common.repository.base_repository import BaseRepository


class CharacterStatRepository(BaseRepository[CharacterStat]):
    def __init__(self, db: AsyncSurreal):
        super().__init__(db, CharacterStat)
        self.table_name = "character_stat"
        self.logger: logging.Logger = logging.getLogger(__name__)