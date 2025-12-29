import logging

from ds_common.models.game_time import GameTime
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class GameTimeRepository(BaseRepository[GameTime]):
    """
    Repository for GameTime model (singleton pattern).
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, GameTime)
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def get_game_time(self) -> GameTime | None:
        """
        Get the current game time record (singleton).

        Returns:
            GameTime instance or None if not initialized
        """
        all_times = await self.get_all()
        if all_times:
            return all_times[0]
        return None

    async def initialize_game_time(self) -> GameTime:
        """
        Initialize game time if it doesn't exist.

        Returns:
            GameTime instance
        """
        existing = await self.get_game_time()
        if existing:
            return existing

        game_time = GameTime()
        return await self.create(game_time)

    async def update_game_time(self, game_time: GameTime) -> GameTime:
        """
        Update the game time record.

        Args:
            game_time: GameTime instance to update

        Returns:
            Updated GameTime instance
        """
        return await self.update(game_time)
