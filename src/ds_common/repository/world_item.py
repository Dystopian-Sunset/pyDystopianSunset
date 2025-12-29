import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ds_common.models.world_item import ItemStatus, ItemType, WorldItem
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class WorldItemRepository(BaseRepository[WorldItem]):
    """
    Repository for WorldItem model.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, WorldItem)
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def get_by_status(
        self, status: ItemStatus, session: AsyncSession | None = None
    ) -> list[WorldItem]:
        """
        Get all items with a specific status.

        Args:
            status: Item status to filter by
            session: Optional database session

        Returns:
            List of WorldItem instances
        """
        stmt = select(WorldItem).where(WorldItem.status == status)

        async def _execute(sess: AsyncSession):
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session, read_only=True)

    async def get_by_type(
        self, item_type: ItemType, session: AsyncSession | None = None
    ) -> list[WorldItem]:
        """
        Get all items of a specific type.

        Args:
            item_type: Item type to filter by
            session: Optional database session

        Returns:
            List of WorldItem instances
        """
        stmt = select(WorldItem).where(WorldItem.item_type == item_type)

        async def _execute(sess: AsyncSession):
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session, read_only=True)

    async def get_available(self, session: AsyncSession | None = None) -> list[WorldItem]:
        """
        Get all available items (not collected).

        Args:
            session: Optional database session

        Returns:
            List of WorldItem instances
        """
        return await self.get_by_status("AVAILABLE", session=session)

    async def get_by_quest(
        self, quest_id: UUID, session: AsyncSession | None = None
    ) -> list[WorldItem]:
        """
        Get all items related to a specific quest.

        Args:
            quest_id: Quest ID
            session: Optional database session

        Returns:
            List of WorldItem instances
        """
        all_items = await self.get_all(session=session)
        return [item for item in all_items if quest_id in item.quest_goals]
