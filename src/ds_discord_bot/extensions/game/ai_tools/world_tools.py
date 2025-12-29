"""
World-related AI tools for NPCs and location management.
"""

import logging

from pydantic_ai import RunContext

from ds_common.models.game_master import (
    GMAgentDependencies,
    RequestCreateLocationEdge,
    RequestCreateLocationNode,
    RequestGenerateNPC,
    ResponseLocationEdge,
    ResponseLocationNode,
)
from ds_common.models.npc import NPC
from ds_common.metrics.service import get_metrics_service


async def fetch_npc(
    ctx: RunContext[None],  # noqa: ARG001
    request: RequestGenerateNPC,
) -> NPC:
    """When a NPC character is needed, call this tool to generate or create a new NPC for the player to interact with.

    Args:
        ctx: The context of the agent.
        request: The request to generate or create a new NPC.

    Returns:
        NPC: The generated or created NPC.
    """
    print(
        f"!!! Selecting or creating NPC: {request.name}, {request.race}, {request.background}, {request.profession}, {request.faction}, {request.location}"
    )
    npc = await NPC.generate_npc(
        request.name,
        request.race,
        request.background,
        request.profession,
        request.faction,
        request.location,
    )

    # Log NPC generation (even if not saved yet, this is a world state change)
    logger = logging.getLogger(__name__)
    metrics = get_metrics_service()

    logger.info(
        f"World state change: NPC generated - {npc.name} "
        f"(Race: {npc.race}, Profession: {npc.profession}, "
        f"Level: {npc.level}, Location: {npc.location})"
    )
    metrics.record_world_state_change("npc", "generated")

    return npc


async def create_location_node(
    ctx: RunContext[GMAgentDependencies],
    request: RequestCreateLocationNode,
) -> ResponseLocationNode:
    """
    Create a new location node dynamically during gameplay.
    Use this when the GM creates a new location that should persist in the world graph.

    Args:
        ctx: The context of the agent.
        request: The request to create a location node.

    Returns:
        ResponseLocationNode: The created location node information.
    """
    from ds_common.memory.location_graph_service import LocationGraphService
    from ds_common.repository.location_node import LocationNodeRepository

    postgres_manager = ctx.deps.postgres_manager
    location_graph_service = LocationGraphService(postgres_manager)
    node_repository = LocationNodeRepository(postgres_manager)

    # Find parent location if specified
    parent_location_id = None
    if request.parent_location_name:
        parent_node = await node_repository.get_by_location_name(
            request.parent_location_name, case_sensitive=False
        )
        if parent_node:
            parent_location_id = parent_node.id

    # Get game session for discovery tracking
    game_session_id = ctx.deps.game_session.id if ctx.deps.game_session else None
    discovered_by = ctx.deps.action_character.id if ctx.deps.action_character else None

    location_node = await location_graph_service.create_location_node(
        location_name=request.location_name,
        location_type=request.location_type,
        description=request.description,
        theme=request.theme,
        parent_location_id=parent_location_id,
        discovered_by=discovered_by,
        discovered_in_session=game_session_id,
    )

    print(f"!!! Created location node: {request.location_name} ({request.location_type})")

    return ResponseLocationNode(
        location_id=str(location_node.id),
        location_name=location_node.location_name,
        location_type=location_node.location_type,
        message=f"Created location: {location_node.location_name}",
    )


async def create_location_edge(
    ctx: RunContext[GMAgentDependencies],
    request: RequestCreateLocationEdge,
) -> ResponseLocationEdge:
    """
    Create a new location edge (route/connection) between two locations.
    Use this when the GM creates a new route or when a player discovers a connection.

    Args:
        ctx: The context of the agent.
        request: The request to create a location edge.

    Returns:
        ResponseLocationEdge: The created location edge information.
    """
    from ds_common.memory.location_graph_service import LocationGraphService
    from ds_common.repository.location_node import LocationNodeRepository

    postgres_manager = ctx.deps.postgres_manager
    location_graph_service = LocationGraphService(postgres_manager)
    node_repository = LocationNodeRepository(postgres_manager)

    # Find location nodes
    from_node = await node_repository.get_by_location_name(
        request.from_location_name, case_sensitive=False
    )
    to_node = await node_repository.get_by_location_name(
        request.to_location_name, case_sensitive=False
    )

    if not from_node:
        raise ValueError(f"Location not found: {request.from_location_name}")
    if not to_node:
        raise ValueError(f"Location not found: {request.to_location_name}")

    # Get game session for discovery tracking
    game_session_id = ctx.deps.game_session.id if ctx.deps.game_session else None
    discovered_by = ctx.deps.action_character.id if ctx.deps.action_character else None

    location_edge = await location_graph_service.create_location_edge(
        from_location_id=from_node.id,
        to_location_id=to_node.id,
        edge_type=request.edge_type,
        travel_method=request.travel_method,
        travel_time=request.travel_time,
        narrative_description=request.narrative_description,
        discovered_by=discovered_by,
        discovered_in_session=game_session_id,
    )

    print(
        f"!!! Created location edge: {request.from_location_name} -> {request.to_location_name} ({request.edge_type})"
    )

    return ResponseLocationEdge(
        edge_id=str(location_edge.id),
        from_location_name=request.from_location_name,
        to_location_name=request.to_location_name,
        edge_type=request.edge_type,
        message=f"Created route from {request.from_location_name} to {request.to_location_name}",
    )

