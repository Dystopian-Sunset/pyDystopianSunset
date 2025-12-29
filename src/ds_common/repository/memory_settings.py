from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ds_common.models.memory_settings import MemorySettings
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class MemorySettingsRepository(BaseRepository[MemorySettings]):
    """Repository for memory settings operations (singleton pattern)."""

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, MemorySettings)

    async def get_settings(
        self,
        session: AsyncSession | None = None,
    ) -> MemorySettings:
        """
        Get the singleton settings record.

        Creates default settings if none exist.

        Args:
            session: Optional database session

        Returns:
            Memory settings instance
        """
        self.logger.debug("Getting memory settings")

        async def _execute(sess: AsyncSession):
            stmt = select(MemorySettings)
            result = await sess.execute(stmt)
            settings = result.scalar_one_or_none()

            if settings is None:
                # Create default settings
                settings = MemorySettings()
                sess.add(settings)
                await sess.commit()
                await sess.refresh(settings)
                self.logger.info("Created default memory settings")

            return settings

        return await self._with_session(_execute, session)

    async def update_settings(
        self,
        settings: MemorySettings,
        session: AsyncSession | None = None,
    ) -> MemorySettings:
        """
        Update memory settings.

        Args:
            settings: Updated settings
            session: Optional database session

        Returns:
            Updated settings
        """
        return await self.update(settings, session)
