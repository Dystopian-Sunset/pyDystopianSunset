"""
Cooldown-related AI tools for managing character cooldowns.
"""

from pydantic_ai import RunContext

from ds_common.combat.cooldown_service import CooldownService
from ds_common.models.game_master import (
    GMAgentDependencies,
    RequestCheckCooldown,
    RequestGetCooldowns,
    RequestStartCooldown,
    ResponseCheckCooldown,
    ResponseGetCooldowns,
    ResponseStartCooldown,
)
from ds_common.repository.character import CharacterRepository

from .base import get_character_from_context


async def check_character_cooldown(
    ctx: RunContext[GMAgentDependencies],
    request: RequestCheckCooldown,
) -> ResponseCheckCooldown:
    """
    Check if a specific cooldown is currently active for a character.

    Args:
        ctx: The context of the agent.
        request: The request to check cooldown.

    Returns:
        ResponseCheckCooldown: Whether the cooldown is active and remaining time.
    """
    character = get_character_from_context(ctx, request)
    postgres_manager = ctx.deps.postgres_manager

    character_repository = CharacterRepository(postgres_manager)
    character = await character_repository.get_by_id(character.id)

    if not character:
        raise ValueError("Character not found")

    cooldown_service = CooldownService(postgres_manager)
    is_active = await cooldown_service.check_cooldown(
        character, request.cooldown_type, request.cooldown_name
    )
    remaining = await cooldown_service.get_cooldown_remaining(
        character, request.cooldown_type, request.cooldown_name
    )

    return ResponseCheckCooldown(
        character=character,
        cooldown_type=request.cooldown_type,
        cooldown_name=request.cooldown_name,
        is_active=is_active,
        remaining_hours=round(remaining, 2) if remaining is not None else None,
    )


async def get_character_cooldowns(
    ctx: RunContext[GMAgentDependencies],
    request: RequestGetCooldowns,
) -> ResponseGetCooldowns:
    """
    Get all active cooldowns for a character.

    Args:
        ctx: The context of the agent.
        request: The request to get cooldowns.

    Returns:
        ResponseGetCooldowns: List of all active cooldowns.
    """
    character = get_character_from_context(ctx, request)
    postgres_manager = ctx.deps.postgres_manager

    character_repository = CharacterRepository(postgres_manager)
    character = await character_repository.get_by_id(character.id)

    if not character:
        raise ValueError("Character not found")

    cooldown_service = CooldownService(postgres_manager)
    active_cooldowns = await cooldown_service.get_active_cooldowns(character)
    cooldowns_list = []
    for cooldown in active_cooldowns:
        remaining = await cooldown_service.get_cooldown_remaining(
            character, cooldown.cooldown_type, cooldown.cooldown_name
        )
        if remaining is not None:
            cooldowns_list.append(
                {
                    "type": cooldown.cooldown_type,
                    "name": cooldown.cooldown_name,
                    "remaining_hours": round(remaining, 2),
                }
            )

    return ResponseGetCooldowns(character=character, cooldowns=cooldowns_list)


async def start_character_cooldown(
    ctx: RunContext[GMAgentDependencies],
    request: RequestStartCooldown,
) -> ResponseStartCooldown:
    """
    Start a cooldown for a character. Use this when a skill/ability/item is used.

    Args:
        ctx: The context of the agent.
        request: The request to start a cooldown.

    Returns:
        ResponseStartCooldown: The started cooldown information.
    """
    character = get_character_from_context(ctx, request)
    postgres_manager = ctx.deps.postgres_manager

    character_repository = CharacterRepository(postgres_manager)
    character = await character_repository.get_by_id(character.id)

    if not character:
        raise ValueError("Character not found")

    cooldown_service = CooldownService(postgres_manager)
    cooldown = await cooldown_service.start_cooldown(
        character,
        request.cooldown_type,
        request.cooldown_name,
        request.duration_game_hours,
    )

    return ResponseStartCooldown(
        character=character,
        cooldown_type=request.cooldown_type,
        cooldown_name=request.cooldown_name,
        expires_at_game_time=cooldown.expires_at_game_time.isoformat(),
        duration_game_hours=request.duration_game_hours,
    )

