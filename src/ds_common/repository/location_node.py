"""
Repository for LocationNode model.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ds_common.models.location_node import LocationNode
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class LocationNodeRepository(BaseRepository[LocationNode]):
    """
    Repository for LocationNode model with graph query methods.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, LocationNode)
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def get_by_location_name(
        self, location_name: str, case_sensitive: bool = False, session: AsyncSession | None = None
    ) -> LocationNode | None:
        """
        Get location node by location name.

        Args:
            location_name: Name of the location
            case_sensitive: Whether the search should be case sensitive
            session: Optional database session

        Returns:
            LocationNode instance or None
        """
        return await self.get_by_field(
            "location_name",
            location_name,
            case_sensitive=case_sensitive,
            session=session,
            read_only=True,
        )

    async def get_by_location_type(
        self, location_type: str, session: AsyncSession | None = None
    ) -> list[LocationNode]:
        """
        Get all location nodes of a specific type.

        Args:
            location_type: Location type (CITY, DISTRICT, SECTOR, POI, CUSTOM)
            session: Optional database session

        Returns:
            List of LocationNode instances
        """

        async def _execute(sess: AsyncSession):
            stmt = select(LocationNode).where(LocationNode.location_type == location_type)
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session, read_only=True)

    async def get_by_parent_location(
        self, parent_location_id: UUID, session: AsyncSession | None = None
    ) -> list[LocationNode]:
        """
        Get all child location nodes for a parent location.

        Args:
            parent_location_id: Parent location node ID
            session: Optional database session

        Returns:
            List of child LocationNode instances
        """

        async def _execute(sess: AsyncSession):
            stmt = select(LocationNode).where(LocationNode.parent_location_id == parent_location_id)
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session, read_only=True)

    async def get_by_theme(
        self, theme: str, session: AsyncSession | None = None
    ) -> list[LocationNode]:
        """
        Get all location nodes with a specific theme.

        Args:
            theme: Theme name
            session: Optional database session

        Returns:
            List of LocationNode instances
        """

        async def _execute(sess: AsyncSession):
            stmt = select(LocationNode).where(LocationNode.theme == theme)
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session, read_only=True)

    async def get_cities(self, session: AsyncSession | None = None) -> list[LocationNode]:
        """
        Get all city location nodes.

        Args:
            session: Optional database session

        Returns:
            List of city LocationNode instances
        """
        return await self.get_by_location_type("CITY", session=session)
