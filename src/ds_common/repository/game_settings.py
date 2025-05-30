import logging

from surrealdb.data.types.record_id import RecordID

from ds_common.models.game_settings import GameSettings
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.surreal_manager import SurrealManager


class GameSettingsRepository(BaseRepository[GameSettings]):
    def __init__(self, surreal_manager: SurrealManager):
        super().__init__(surreal_manager, GameSettings, "game_settings")
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def seed_db(self) -> GameSettings:
        game_settings = GameSettings(id=RecordID(self.table_name, 1))
        await self.upsert(game_settings)
        return game_settings