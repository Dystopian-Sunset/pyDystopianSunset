"""
Character-related AI tools for credits and location management.
"""

from pydantic_ai import RunContext

from ds_common.models.game_master import (
    GMAgentDependencies,
    RequestAddCredits,
    RequestGetCharacterPurse,
    RequestUpdateCharacterLocation,
    ResponseCharacterCredits,
    ResponseCharacterLocation,
)
from ds_common.repository.character import CharacterRepository
from ds_common.repository.location_node import LocationNodeRepository

from .base import get_character_from_context, refresh_character


async def get_character_credits(
    ctx: RunContext[GMAgentDependencies],
    request: RequestGetCharacterPurse,
) -> ResponseCharacterCredits:
    """Fetch the current state of a character's credits from the database. The default currency is the 'quill' if none other specified.

    Args:
        ctx: The context of the agent.
        request: The request to get the character's credits.

    Returns:
        ResponseCharacterCredits: The current state of the character's credits.
    """
    character = get_character_from_context(ctx, request)
    postgres_manager = ctx.deps.postgres_manager

    character_repository = CharacterRepository(postgres_manager)
    character = await character_repository.get_by_id(character.id)

    if not character:
        raise ValueError("Character not found")

    print(f"!!! Player credits: {character.credits}")

    return ResponseCharacterCredits(
        character=character,
        credits=character.credits,
        currency=request.currency,
    )


async def adjust_character_credits(
    ctx: RunContext[GMAgentDependencies],
    request: RequestAddCredits,
) -> ResponseCharacterCredits:
    """Anytime that a character's credits need to be adjusted, call this tool. This could be for purchases, sales, rewards, or other actions that affect character's wallet status.

    Args:
        ctx: The context of the agent.
        request: The request to adjust credits (amount can be positive or negative).

    Returns:
        ResponseCharacterCredits: The updated state of the character's credits.
    """
    character = get_character_from_context(ctx, request)
    postgres_manager = ctx.deps.postgres_manager

    character_repository = CharacterRepository(postgres_manager)
    character = await character_repository.get_by_id(character.id)

    if not character:
        raise ValueError("Character not found")

    if request.amount < 0 and character.credits + request.amount < 0:
        raise ValueError("Not enough credits")

    character.credits += request.amount
    await character_repository.update(character)

    print(f"!!! Adjust credits: {request.amount}, new credits: {character.credits}")

    return ResponseCharacterCredits(
        character=character,
        credits=character.credits,
        currency=request.currency,
    )


async def update_character_location(
    ctx: RunContext[GMAgentDependencies],
    request: RequestUpdateCharacterLocation,
) -> ResponseCharacterLocation:
    """
    Update a character's current location.
    Call this when a character successfully travels to a new location.

    Args:
        ctx: The context of the agent.
        request: The request to update character location.

    Returns:
        ResponseCharacterLocation: The updated character location information.
    """
    character = get_character_from_context(ctx, request)
    postgres_manager = ctx.deps.postgres_manager

    character_repository = CharacterRepository(postgres_manager)
    node_repository = LocationNodeRepository(postgres_manager)

    # Get fresh character
    character = await character_repository.get_by_id(character.id)
    if not character:
        raise ValueError("Character not found")

    # Track old location for memory
    old_location_id = character.current_location
    old_location_name = None
    if old_location_id:
        old_location_node = await node_repository.get_by_id(old_location_id)
        if old_location_node:
            old_location_name = old_location_node.location_name

    # Find location node
    location_node = await node_repository.get_by_location_name(
        request.location_name, case_sensitive=False
    )

    if not location_node:
        raise ValueError(f"Location not found: {request.location_name}")

    # Only update if location actually changed
    location_changed = old_location_id != location_node.id

    if location_changed:
        # Update character location
        character.current_location = location_node.id
        await character_repository.update(character)

        # Create memory event for location change
        try:
            import logging

            from openai import AsyncOpenAI

            from ds_common.config_bot import get_config
            from ds_common.memory.memory_processor import MemoryProcessor

            # Only capture if embedding service is available
            config = get_config()
            embedding_base_url = config.ai_embedding_base_url
            embedding_api_key = config.ai_embedding_api_key

            if embedding_base_url or embedding_api_key:
                # Build client kwargs
                client_kwargs = {
                    "api_key": embedding_api_key
                    if embedding_api_key
                    else "sk-ollama-local-dummy-key-not-used"
                }
                if embedding_base_url:
                    client_kwargs["base_url"] = embedding_base_url

                openai_client = AsyncOpenAI(**client_kwargs)
                embedding_model = config.ai_embedding_model
                embedding_dimensions = config.ai_embedding_dimensions

                # Try to get Redis client for memory embeddings
                redis_client = None
                try:
                    import redis.asyncio as redis

                    redis_url = config.redis_url
                    if redis_url:
                        redis_client = await redis.from_url(
                            redis_url, db=config.redis_db_memory, decode_responses=False
                        )
                except Exception:
                    # Redis not available, continue without it
                    pass

                memory_processor = MemoryProcessor(
                    postgres_manager,
                    openai_client,
                    redis_client=redis_client,
                    embedding_model=embedding_model,
                    embedding_dimensions=embedding_dimensions,
                )

                # Get location context for new location (parent, city, region info)
                location_info = {
                    "current_location": request.location_name,
                    "location_type": location_node.location_type,
                }

                # Get parent location if available
                if location_node.parent_location_id:
                    parent_node = await node_repository.get_by_id(
                        location_node.parent_location_id
                    )
                    if parent_node:
                        location_info["parent_location"] = parent_node.location_name

                # Get region/city information from location fact
                if location_node.location_fact_id:
                    from ds_common.repository.location_fact import LocationFactRepository
                    from ds_common.repository.world_region import WorldRegionRepository

                    fact_repo = LocationFactRepository(postgres_manager)
                    location_fact = await fact_repo.get_by_id(location_node.location_fact_id)
                    if location_fact and location_fact.region_id:
                        region_repo = WorldRegionRepository(postgres_manager)
                        region = await region_repo.get_by_id(location_fact.region_id)
                        if region:
                            if region.hierarchy_level == 0:  # City
                                location_info["city"] = region.name
                            elif region.hierarchy_level == 1:  # District
                                location_info["district"] = region.name
                                if region.parent_region_id:
                                    parent_region = await region_repo.get_by_id(
                                        region.parent_region_id
                                    )
                                    if parent_region:
                                        location_info["city"] = parent_region.name
                            elif region.hierarchy_level == 2:  # Sector
                                location_info["sector"] = region.name
                                if region.parent_region_id:
                                    parent_region = await region_repo.get_by_id(
                                        region.parent_region_id
                                    )
                                    if parent_region:
                                        location_info["district"] = parent_region.name
                                        if parent_region.parent_region_id:
                                            grandparent_region = await region_repo.get_by_id(
                                                parent_region.parent_region_id
                                            )
                                            if grandparent_region:
                                                location_info["city"] = grandparent_region.name

                # Fallback: infer from location_type
                if not location_info.get("city") and location_node.location_type == "CITY":
                    location_info["city"] = request.location_name

                # Store location details (description, atmosphere, theme, etc.) for persistence
                if location_node.description:
                    location_info["description"] = location_node.description[:500]
                if location_node.atmosphere:
                    location_info["atmosphere"] = location_node.atmosphere
                if location_node.theme:
                    location_info["theme"] = location_node.theme
                if location_node.physical_properties:
                    location_info["physical_properties"] = location_node.physical_properties
                if location_node.character_associations:
                    location_info["character_associations"] = (
                        location_node.character_associations
                    )

                # Build location searchable text
                location_parts = [request.location_name]
                if location_info.get("parent_location"):
                    location_parts.append(location_info["parent_location"])
                if location_info.get("city"):
                    location_parts.append(location_info["city"])
                location_info["location_searchable"] = " ".join(location_parts)
                location_info["location_id"] = str(location_node.id)

                # Create location change memory event with full context
                travel_description = f"Traveled from {old_location_name or 'unknown location'} to {request.location_name}"
                content = {
                    "action": "location_change",
                    "description": travel_description,
                    "from_location": old_location_name,
                    "to_location": request.location_name,
                    "response": f"{character.name} arrived at {request.location_name}",
                    "location_context": location_info,
                }

                logger = logging.getLogger(__name__)
                await memory_processor.capture_session_event(
                    session_id=ctx.deps.game_session.id,
                    character_id=character.id,
                    memory_type="action",
                    content=content,
                    participants=None,
                    location_id=location_node.id,
                )
                logger.info(
                    f"Created memory event for {character.name} location change: {old_location_name} -> {request.location_name}"
                )
        except Exception as e:
            # Don't fail location update if memory capture fails
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                f"Failed to create memory event for location change: {e}", exc_info=True
            )

        logger = logging.getLogger(__name__)
        logger.info(
            f"Updated {character.name} location from {old_location_name or 'unknown'} to {request.location_name}"
        )
    else:
        logger = logging.getLogger(__name__)
        logger.debug(
            f"{character.name} is already at {request.location_name}, no update needed"
        )

    return ResponseCharacterLocation(
        character=character,
        location_name=request.location_name,
        location_id=str(location_node.id),
        message=f"{character.name} is now at {request.location_name}",
    )

