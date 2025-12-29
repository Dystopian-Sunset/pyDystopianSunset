"""
Location graph service for graph-based location operations.
"""

import logging
from uuid import UUID

from ds_common.metrics.service import get_metrics_service
from ds_common.models.location_edge import LocationEdge
from ds_common.models.location_node import LocationNode
from ds_common.repository.location_edge import LocationEdgeRepository
from ds_common.repository.location_node import LocationNodeRepository
from ds_discord_bot.postgres_manager import PostgresManager


class LocationGraphService:
    """
    Service for location graph operations including pathfinding and discovery.
    """

    def __init__(self, postgres_manager: PostgresManager):
        """
        Initialize the location graph service.

        Args:
            postgres_manager: PostgreSQL manager instance
        """
        self.logger = logging.getLogger(__name__)
        self.postgres_manager = postgres_manager
        self.node_repo = LocationNodeRepository(postgres_manager)
        self.edge_repo = LocationEdgeRepository(postgres_manager)
        self.metrics = get_metrics_service()

    async def create_location_node(
        self,
        location_name: str,
        location_type: str,
        description: str | None = None,
        atmosphere: dict | None = None,
        physical_properties: dict | None = None,
        theme: str | None = None,
        character_associations: dict | None = None,
        location_fact_id: UUID | None = None,
        parent_location_id: UUID | None = None,
        discovered_by: UUID | None = None,
        discovered_in_session: UUID | None = None,
    ) -> LocationNode:
        """
        Create a new location node.

        Args:
            location_name: Name of the location
            location_type: Type of location (CITY, DISTRICT, SECTOR, POI, CUSTOM)
            description: Rich narrative description
            atmosphere: Sensory details
            physical_properties: Physical properties
            theme: Theme name
            character_associations: Character associations
            location_fact_id: Related LocationFact ID
            parent_location_id: Parent location node ID
            discovered_by: Character who discovered this location
            discovered_in_session: Game session where discovered

        Returns:
            Created LocationNode instance
        """
        from datetime import UTC, datetime

        location_node = LocationNode(
            location_name=location_name,
            location_type=location_type,
            description=description,
            atmosphere=atmosphere,
            physical_properties=physical_properties,
            theme=theme,
            character_associations=character_associations,
            location_fact_id=location_fact_id,
            parent_location_id=parent_location_id,
            discovered_by=discovered_by,
            discovered_at=datetime.now(UTC) if discovered_by else None,
            discovered_in_session=discovered_in_session,
        )

        created_node = await self.node_repo.create(location_node)
        
        # Log and record metrics for world state change
        self.logger.info(
            f"World state change: Location node created - {created_node.location_name} "
            f"(ID: {created_node.id}, Type: {created_node.location_type}, "
            f"Discovered by: {discovered_by}, Parent: {parent_location_id})"
        )
        self.metrics.record_world_state_change("location_node", "created")
        
        return created_node

    async def create_location_edge(
        self,
        from_location_id: UUID,
        to_location_id: UUID,
        edge_type: str,
        travel_method: str | None = None,
        travel_time: str | None = None,
        requirements: dict | None = None,
        narrative_description: str | None = None,
        conditions: dict | None = None,
        discovered_by: UUID | None = None,
        discovered_in_session: UUID | None = None,
    ) -> LocationEdge:
        """
        Create a new location edge (connection/route).

        Args:
            from_location_id: Source location node ID
            to_location_id: Destination location node ID
            edge_type: Edge type (DIRECT, REQUIRES_TRAVEL, SECRET, CONDITIONAL)
            travel_method: Travel method
            travel_time: Travel time
            requirements: Travel requirements
            narrative_description: Narrative description
            conditions: Route conditions
            discovered_by: Character who discovered this route
            discovered_in_session: Game session where discovered

        Returns:
            Created LocationEdge instance
        """
        from datetime import UTC, datetime

        location_edge = LocationEdge(
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            edge_type=edge_type,
            travel_method=travel_method,
            travel_time=travel_time,
            requirements=requirements,
            narrative_description=narrative_description,
            conditions=conditions,
            discovered_by=discovered_by,
            discovered_at=datetime.now(UTC) if discovered_by else None,
            discovered_in_session=discovered_in_session,
        )

        created_edge = await self.edge_repo.create(location_edge)
        
        # Log and record metrics for world state change
        self.logger.info(
            f"World state change: Location edge created - "
            f"From: {from_location_id}, To: {to_location_id} "
            f"(ID: {created_edge.id}, Type: {edge_type}, "
            f"Discovered by: {discovered_by})"
        )
        self.metrics.record_world_state_change("location_edge", "created")
        
        return created_edge

    async def get_connected_locations(
        self,
        location_id: UUID,
        edge_type: str | None = None,
        include_incoming: bool = False,
    ) -> list[LocationNode]:
        """
        Get all locations connected to a location node.

        Args:
            location_id: Location node ID
            edge_type: Optional filter by edge type
            include_incoming: If True, include locations with incoming edges

        Returns:
            List of connected LocationNode instances
        """
        connected_ids = await self.edge_repo.get_connected_locations(
            location_id, edge_type=edge_type
        )

        if include_incoming:
            incoming_edges = await self.edge_repo.get_incoming_edges(location_id)
            if edge_type:
                incoming_edges = [e for e in incoming_edges if e.edge_type == edge_type]
            connected_ids.extend([edge.from_location_id for edge in incoming_edges])

        # Remove duplicates
        connected_ids = list(set(connected_ids))

        # Fetch location nodes
        locations = []
        for loc_id in connected_ids:
            node = await self.node_repo.get_by_id(loc_id)
            if node:
                locations.append(node)

        return locations

    async def find_path(
        self,
        from_location_id: UUID,
        to_location_id: UUID,
        max_depth: int = 10,
        allowed_edge_types: list[str] | None = None,
    ) -> list[LocationNode] | None:
        """
        Find a path between two locations using breadth-first search.

        Args:
            from_location_id: Starting location node ID
            to_location_id: Destination location node ID
            max_depth: Maximum path depth to search
            allowed_edge_types: Optional list of allowed edge types

        Returns:
            List of LocationNode instances representing the path, or None if no path found
        """
        if from_location_id == to_location_id:
            node = await self.node_repo.get_by_id(from_location_id)
            return [node] if node else None

        # BFS to find shortest path
        from collections import deque

        queue = deque([(from_location_id, [from_location_id])])
        visited = {from_location_id}

        depth = 0
        while queue and depth < max_depth:
            level_size = len(queue)
            for _ in range(level_size):
                current_id, path = queue.popleft()

                # Get outgoing edges
                edges = await self.edge_repo.get_outgoing_edges(current_id)
                if allowed_edge_types:
                    edges = [e for e in edges if e.edge_type in allowed_edge_types]

                for edge in edges:
                    next_id = edge.to_location_id

                    if next_id == to_location_id:
                        # Found path, reconstruct and return
                        path_nodes = []
                        for node_id in path + [next_id]:
                            node = await self.node_repo.get_by_id(node_id)
                            if node:
                                path_nodes.append(node)
                        return path_nodes if len(path_nodes) == len(path) + 1 else None

                    if next_id not in visited:
                        visited.add(next_id)
                        queue.append((next_id, path + [next_id]))

            depth += 1

        return None

    async def discover_route(
        self,
        from_location_id: UUID,
        to_location_id: UUID,
        edge_type: str,
        discovered_by: UUID,
        discovered_in_session: UUID,
        travel_method: str | None = None,
        travel_time: str | None = None,
        requirements: dict | None = None,
        narrative_description: str | None = None,
        conditions: dict | None = None,
    ) -> LocationEdge:
        """
        Discover and create a new route between locations.

        Args:
            from_location_id: Source location node ID
            to_location_id: Destination location node ID
            edge_type: Edge type
            discovered_by: Character who discovered the route
            discovered_in_session: Game session where discovered
            travel_method: Travel method
            travel_time: Travel time
            requirements: Travel requirements
            narrative_description: Narrative description
            conditions: Route conditions

        Returns:
            Created LocationEdge instance
        """
        return await self.create_location_edge(
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            edge_type=edge_type,
            travel_method=travel_method,
            travel_time=travel_time,
            requirements=requirements,
            narrative_description=narrative_description,
            conditions=conditions,
            discovered_by=discovered_by,
            discovered_in_session=discovered_in_session,
        )

    async def get_discoverable_routes(
        self, location_id: UUID, edge_type: str | None = None
    ) -> list[LocationEdge]:
        """
        Get routes that can be discovered from a location (existing but not yet discovered).

        Args:
            location_id: Location node ID
            edge_type: Optional filter by edge type

        Returns:
            List of LocationEdge instances that are discoverable
        """
        edges = await self.edge_repo.get_outgoing_edges(location_id)
        if edge_type:
            edges = [e for e in edges if e.edge_type == edge_type]

        # Filter for routes that exist but haven't been discovered yet
        # (discovered_by is None or discovered_at is None)
        discoverable = [e for e in edges if e.discovered_by is None or e.discovered_at is None]

        return discoverable
