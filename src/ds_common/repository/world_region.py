import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ds_common.models.world_region import RegionType, WorldRegion
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class WorldRegionRepository(BaseRepository[WorldRegion]):
    """
    Repository for WorldRegion model.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, WorldRegion)
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def get_by_type(
        self, region_type: RegionType, session: AsyncSession | None = None
    ) -> list[WorldRegion]:
        """
        Get all regions of a specific type.

        Args:
            region_type: Region type to filter by
            session: Optional database session

        Returns:
            List of WorldRegion instances
        """
        stmt = select(WorldRegion).where(WorldRegion.region_type == region_type)

        async def _execute(sess: AsyncSession):
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)

    async def get_by_parent(
        self, parent_id: UUID, session: AsyncSession | None = None
    ) -> list[WorldRegion]:
        """
        Get all child regions of a parent region.

        Args:
            parent_id: Parent region ID
            session: Optional database session

        Returns:
            List of WorldRegion instances
        """
        stmt = select(WorldRegion).where(WorldRegion.parent_region_id == parent_id)

        async def _execute(sess: AsyncSession):
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)

    async def get_by_faction(
        self, faction: str, session: AsyncSession | None = None
    ) -> list[WorldRegion]:
        """
        Get all regions associated with a specific faction.

        Args:
            faction: Faction name
            session: Optional database session

        Returns:
            List of WorldRegion instances
        """
        all_regions = await self.get_all(session=session)
        return [r for r in all_regions if faction in r.factions]

    async def get_by_city(
        self, city: str, session: AsyncSession | None = None
    ) -> list[WorldRegion]:
        """
        Get all regions in a specific city.

        Args:
            city: City name
            session: Optional database session

        Returns:
            List of WorldRegion instances
        """
        stmt = select(WorldRegion).where(WorldRegion.city == city)

        async def _execute(sess: AsyncSession):
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)
