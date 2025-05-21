import logging

from surrealdb import AsyncSurreal

from ds_common.models.game_settings import GameSettings
from ds_common.repository.base_repository import BaseRepository


class GameSettingsRepository(BaseRepository[GameSettings]):
    def __init__(self, db: AsyncSurreal):
        super().__init__(db, GameSettings)
        self.table_name = "game_settings"
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def seed_db(self) -> GameSettings:
        game_settings = GameSettings()
        await self.insert(game_settings)
        return game_settings