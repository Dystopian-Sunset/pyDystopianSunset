"""
Repository for LocationEdge model.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ds_common.models.location_edge import LocationEdge
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class LocationEdgeRepository(BaseRepository[LocationEdge]):
    """
    Repository for LocationEdge model with connection and pathfinding queries.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, LocationEdge)
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def get_outgoing_edges(
        self, from_location_id: UUID, session: AsyncSession | None = None
    ) -> list[LocationEdge]:
        """
        Get all outgoing edges from a location.

        Args:
            from_location_id: Source location node ID
            session: Optional database session

        Returns:
            List of outgoing LocationEdge instances
        """

        async def _execute(sess: AsyncSession):
            stmt = select(LocationEdge).where(LocationEdge.from_location_id == from_location_id)
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)

    async def get_incoming_edges(
        self, to_location_id: UUID, session: AsyncSession | None = None
    ) -> list[LocationEdge]:
        """
        Get all incoming edges to a location.

        Args:
            to_location_id: Destination location node ID
            session: Optional database session

        Returns:
            List of incoming LocationEdge instances
        """

        async def _execute(sess: AsyncSession):
            stmt = select(LocationEdge).where(LocationEdge.to_location_id == to_location_id)
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)

    async def get_edges_between(
        self,
        from_location_id: UUID,
        to_location_id: UUID,
        session: AsyncSession | None = None,
    ) -> list[LocationEdge]:
        """
        Get all edges between two locations.

        Args:
            from_location_id: Source location node ID
            to_location_id: Destination location node ID
            session: Optional database session

        Returns:
            List of LocationEdge instances
        """

        async def _execute(sess: AsyncSession):
            stmt = select(LocationEdge).where(
                LocationEdge.from_location_id == from_location_id,
                LocationEdge.to_location_id == to_location_id,
            )
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)

    async def get_edges_by_type(
        self, edge_type: str, session: AsyncSession | None = None
    ) -> list[LocationEdge]:
        """
        Get all edges of a specific type.

        Args:
            edge_type: Edge type (DIRECT, REQUIRES_TRAVEL, SECRET, CONDITIONAL)
            session: Optional database session

        Returns:
            List of LocationEdge instances
        """

        async def _execute(sess: AsyncSession):
            stmt = select(LocationEdge).where(LocationEdge.edge_type == edge_type)
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        return await self._with_session(_execute, session)

    async def get_connected_locations(
        self, location_id: UUID, edge_type: str | None = None, session: AsyncSession | None = None
    ) -> list[UUID]:
        """
        Get all location IDs connected to a location (outgoing edges).

        Args:
            location_id: Location node ID
            edge_type: Optional filter by edge type
            session: Optional database session

        Returns:
            List of connected location node IDs
        """
        edges = await self.get_outgoing_edges(location_id, session=session)
        if edge_type:
            edges = [e for e in edges if e.edge_type == edge_type]
        return [edge.to_location_id for edge in edges]
