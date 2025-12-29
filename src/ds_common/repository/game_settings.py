import logging
from uuid import UUID

from ds_common.models.game_settings import GameSettings
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class GameSettingsRepository(BaseRepository[GameSettings]):
    """
    Repository for GameSettings model.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, GameSettings)
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def get_settings(self) -> GameSettings:
        """
        Get the singleton game settings record.

        Creates default settings if none exist.

        Returns:
            GameSettings instance
        """
        # Using a fixed UUID for the default settings
        default_id = UUID("00000000-0000-0000-0000-000000000001")
        existing = await self.get_by_id(default_id)
        if existing:
            return existing

        # Create new default settings if none exist
        return await self.seed_db()

    async def seed_db(self) -> GameSettings:
        """
        Seed the database with default game settings.

        Returns:
            GameSettings instance
        """
        # Try to get existing default settings
        # Using a fixed UUID for the default settings
        default_id = UUID("00000000-0000-0000-0000-000000000001")
        existing = await self.get_by_id(default_id)
        if existing:
            return existing

        # Create new default settings
        game_settings = GameSettings(id=default_id)
        return await self.create(game_settings)
