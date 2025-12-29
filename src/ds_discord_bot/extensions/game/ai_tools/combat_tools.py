"""
Combat-related AI tools for managing character combat and resources.
"""

from pydantic_ai import RunContext

from ds_common.combat import (
    apply_damage,
    apply_healing,
    consume_stamina,
    consume_tech_power,
    format_combat_status,
    format_resource_display,
    restore_stamina,
    restore_tech_power,
)
from uuid import UUID

from ds_common.combat import update_armor
from ds_common.combat.cooldown_service import CooldownService
from ds_common.combat.models import DamageType
from ds_common.models.character import Character
from ds_common.models.game_master import (
    GMAgentDependencies,
    RequestApplyDamage,
    RequestApplyHealing,
    RequestConsumeResource,
    RequestRestoreResource,
    ResponseCombatStatus,
)
from ds_common.repository.character import CharacterRepository
from ds_common.repository.npc import NPCRepository

from .base import get_character_from_context


async def apply_character_damage(
    ctx: RunContext[GMAgentDependencies],
    request: RequestApplyDamage,
) -> ResponseCombatStatus:
    """Apply damage to a character during combat or other dangerous situations.

    Args:
        ctx: The context of the agent.
        request: The request to apply damage.

    Returns:
        ResponseCombatStatus: The character's updated combat status.
    """
    character = get_character_from_context(ctx, request)
    postgres_manager = ctx.deps.postgres_manager

    character_repository = CharacterRepository(postgres_manager)
    character = await character_repository.get_by_id(character.id)

    if not character:
        raise ValueError("Character not found")

    # Map damage type string to enum
    damage_type_map = {
        "physical": DamageType.PHYSICAL,
        "tech": DamageType.TECH,
        "environmental": DamageType.ENVIRONMENTAL,
    }
    damage_type = damage_type_map.get(request.damage_type.lower(), DamageType.PHYSICAL)

    # Apply damage
    result = apply_damage(character, request.damage_amount, damage_type)
    await character_repository.update(character)

    # Format response
    resources = format_resource_display(character)
    status_message = result.message or f"Took {request.damage_amount:.1f} damage"

    print(
        f"!!! Applied damage: {request.damage_amount} {request.damage_type} to {character.name}"
    )

    return ResponseCombatStatus(
        character=character,
        health=resources["current_health"],
        max_health=resources["max_health"],
        stamina=resources["current_stamina"],
        max_stamina=resources["max_stamina"],
        tech_power=resources["current_tech_power"],
        max_tech_power=resources["max_tech_power"],
        armor=resources["current_armor"],
        max_armor=resources["max_armor"],
        is_incapacitated=resources["is_incapacitated"],
        status_message=status_message,
    )


async def apply_character_healing(
    ctx: RunContext[GMAgentDependencies],
    request: RequestApplyHealing,
) -> ResponseCombatStatus:
    """Apply healing to a character.

    Args:
        ctx: The context of the agent.
        request: The request to apply healing.

    Returns:
        ResponseCombatStatus: The character's updated combat status.
    """
    character = get_character_from_context(ctx, request)
    postgres_manager = ctx.deps.postgres_manager

    character_repository = CharacterRepository(postgres_manager)
    character = await character_repository.get_by_id(character.id)

    if not character:
        raise ValueError("Character not found")

    # Apply healing
    result = apply_healing(character, request.heal_amount)
    await character_repository.update(character)

    # Format response
    resources = format_resource_display(character)
    status_message = result.message or f"Healed {request.heal_amount:.1f} health"

    print(f"!!! Applied healing: {request.heal_amount} to {character.name}")

    return ResponseCombatStatus(
        character=character,
        health=resources["current_health"],
        max_health=resources["max_health"],
        stamina=resources["current_stamina"],
        max_stamina=resources["max_stamina"],
        tech_power=resources["current_tech_power"],
        max_tech_power=resources["max_tech_power"],
        armor=resources["current_armor"],
        max_armor=resources["max_armor"],
        is_incapacitated=resources["is_incapacitated"],
        status_message=status_message,
    )


async def consume_character_resource(
    ctx: RunContext[GMAgentDependencies],
    request: RequestConsumeResource,
) -> ResponseCombatStatus:
    """Consume stamina or tech power from a character.

    Args:
        ctx: The context of the agent.
        request: The request to consume a resource.

    Returns:
        ResponseCombatStatus: The character's updated combat status.
    """
    character = get_character_from_context(ctx, request)
    postgres_manager = ctx.deps.postgres_manager

    character_repository = CharacterRepository(postgres_manager)
    character = await character_repository.get_by_id(character.id)

    if not character:
        raise ValueError("Character not found")

    resource_type = request.resource_type.lower()
    if resource_type == "stamina":
        success = consume_stamina(character, request.amount)
        status_message = (
            f"Consumed {request.amount:.1f} stamina"
            if success
            else f"Not enough stamina (needed {request.amount:.1f})"
        )
    elif resource_type == "tech_power":
        success = consume_tech_power(character, request.amount)
        status_message = (
            f"Consumed {request.amount:.1f} tech power"
            if success
            else f"Not enough tech power (needed {request.amount:.1f})"
        )
    else:
        raise ValueError(f"Invalid resource type: {request.resource_type}")

    await character_repository.update(character)

    # Format response
    resources = format_resource_display(character)

    print(f"!!! Consumed {request.resource_type}: {request.amount} from {character.name}")

    return ResponseCombatStatus(
        character=character,
        health=resources["current_health"],
        max_health=resources["max_health"],
        stamina=resources["current_stamina"],
        max_stamina=resources["max_stamina"],
        tech_power=resources["current_tech_power"],
        max_tech_power=resources["max_tech_power"],
        armor=resources["current_armor"],
        max_armor=resources["max_armor"],
        is_incapacitated=resources["is_incapacitated"],
        status_message=status_message,
    )


async def restore_character_resource(
    ctx: RunContext[GMAgentDependencies],
    request: RequestRestoreResource,
) -> ResponseCombatStatus:
    """Restore stamina or tech power to a character.

    Args:
        ctx: The context of the agent.
        request: The request to restore a resource.

    Returns:
        ResponseCombatStatus: The character's updated combat status.
    """
    character = get_character_from_context(ctx, request)
    postgres_manager = ctx.deps.postgres_manager

    character_repository = CharacterRepository(postgres_manager)
    character = await character_repository.get_by_id(character.id)

    if not character:
        raise ValueError("Character not found")

    resource_type = request.resource_type.lower()
    if resource_type == "stamina":
        result = restore_stamina(character, request.amount)
        status_message = result.message or f"Restored {request.amount:.1f} stamina"
    elif resource_type == "tech_power":
        result = restore_tech_power(character, request.amount)
        status_message = result.message or f"Restored {request.amount:.1f} tech power"
    else:
        raise ValueError(f"Invalid resource type: {request.resource_type}")

    await character_repository.update(character)

    # Format response
    resources = format_resource_display(character)

    print(f"!!! Restored {request.resource_type}: {request.amount} to {character.name}")

    return ResponseCombatStatus(
        character=character,
        health=resources["current_health"],
        max_health=resources["max_health"],
        stamina=resources["current_stamina"],
        max_stamina=resources["max_stamina"],
        tech_power=resources["current_tech_power"],
        max_tech_power=resources["max_tech_power"],
        armor=resources["current_armor"],
        max_armor=resources["max_armor"],
        is_incapacitated=resources["is_incapacitated"],
        status_message=status_message,
    )


async def get_character_combat_status(
    ctx: RunContext[GMAgentDependencies],
    character: Character,
) -> ResponseCombatStatus:
    """Get the current combat resource status for a character.

    Args:
        ctx: The context of the agent.
        character: The character to get status for.

    Returns:
        ResponseCombatStatus: The character's current combat status.
    """
    action_character = ctx.deps.action_character
    if not action_character:
        action_character = character
    if not action_character:
        raise ValueError("No character available")

    postgres_manager = ctx.deps.postgres_manager
    character_repository = CharacterRepository(postgres_manager)
    character = await character_repository.get_by_id(action_character.id)

    if not character:
        raise ValueError("Character not found")

    # Format response
    resources = format_resource_display(character)
    status_message = format_combat_status(character)

    # Get active cooldowns
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

    return ResponseCombatStatus(
        character=character,
        health=resources["current_health"],
        max_health=resources["max_health"],
        stamina=resources["current_stamina"],
        max_stamina=resources["max_stamina"],
        tech_power=resources["current_tech_power"],
        max_tech_power=resources["max_tech_power"],
        armor=resources["current_armor"],
        max_armor=resources["max_armor"],
        is_incapacitated=resources["is_incapacitated"],
        status_message=status_message,
        cooldowns=cooldowns_list if cooldowns_list else None,
    )


async def apply_npc_damage(
    ctx: RunContext[GMAgentDependencies],
    npc_id: str,
    damage_amount: float,
    damage_type: str = "physical",
) -> ResponseCombatStatus:
    """Apply damage to an NPC during combat or other dangerous situations.

    Args:
        ctx: The context of the agent.
        npc_id: The NPC ID to apply damage to.
        damage_amount: Amount of damage to apply.
        damage_type: Type of damage ("physical", "tech", or "environmental").

    Returns:
        ResponseCombatStatus: The NPC's updated combat status.
    """
    postgres_manager = ctx.deps.postgres_manager
    npc_repository = NPCRepository(postgres_manager)

    npc = await npc_repository.get_by_id(UUID(npc_id))
    if not npc:
        raise ValueError(f"NPC {npc_id} not found")

    # Map damage type string to enum
    damage_type_map = {
        "physical": DamageType.PHYSICAL,
        "tech": DamageType.TECH,
        "environmental": DamageType.ENVIRONMENTAL,
    }
    damage_type_enum = damage_type_map.get(damage_type.lower(), DamageType.PHYSICAL)

    # Apply damage
    from ds_common.combat import apply_damage

    result = apply_damage(npc, damage_amount, damage_type_enum)
    await npc_repository.update(npc)

    # Format response (NPCs use same format as characters)
    from ds_common.combat import format_resource_display

    resources = format_resource_display(npc)
    status_message = result.message or f"Took {damage_amount:.1f} damage"

    print(f"!!! Applied damage: {damage_amount} {damage_type} to NPC {npc.name}")

    # Create a Character-like object for response (NPCs share the same structure)
    # We'll use the NPC's data to create a minimal Character object for the response
    from ds_common.models.character import Character

    npc_character = Character(
        id=npc.id,
        name=npc.name,
        current_health=npc.current_health,
        max_health=npc.max_health,
        current_stamina=npc.current_stamina,
        max_stamina=npc.max_stamina,
        current_tech_power=npc.current_tech_power,
        max_tech_power=npc.max_tech_power,
        current_armor=npc.current_armor,
        max_armor=npc.max_armor,
        is_incapacitated=npc.is_incapacitated,
    )

    return ResponseCombatStatus(
        character=npc_character,
        health=resources["current_health"],
        max_health=resources["max_health"],
        stamina=resources["current_stamina"],
        max_stamina=resources["max_stamina"],
        tech_power=resources["current_tech_power"],
        max_tech_power=resources["max_tech_power"],
        armor=resources["current_armor"],
        max_armor=resources["max_armor"],
        is_incapacitated=resources["is_incapacitated"],
        status_message=status_message,
    )


async def apply_npc_healing(
    ctx: RunContext[GMAgentDependencies],
    npc_id: str,
    heal_amount: float,
) -> ResponseCombatStatus:
    """Apply healing to an NPC.

    Args:
        ctx: The context of the agent.
        npc_id: The NPC ID to heal.
        heal_amount: Amount of health to restore.

    Returns:
        ResponseCombatStatus: The NPC's updated combat status.
    """
    postgres_manager = ctx.deps.postgres_manager
    npc_repository = NPCRepository(postgres_manager)

    npc = await npc_repository.get_by_id(UUID(npc_id))
    if not npc:
        raise ValueError(f"NPC {npc_id} not found")

    # Apply healing
    from ds_common.combat import apply_healing

    result = apply_healing(npc, heal_amount)
    await npc_repository.update(npc)

    # Format response
    from ds_common.combat import format_resource_display

    resources = format_resource_display(npc)
    status_message = result.message or f"Healed {heal_amount:.1f} health"

    print(f"!!! Applied healing: {heal_amount} to NPC {npc.name}")

    # Create a Character-like object for response
    from ds_common.models.character import Character

    npc_character = Character(
        id=npc.id,
        name=npc.name,
        current_health=npc.current_health,
        max_health=npc.max_health,
        current_stamina=npc.current_stamina,
        max_stamina=npc.max_stamina,
        current_tech_power=npc.current_tech_power,
        max_tech_power=npc.max_tech_power,
        current_armor=npc.current_armor,
        max_armor=npc.max_armor,
        is_incapacitated=npc.is_incapacitated,
    )

    return ResponseCombatStatus(
        character=npc_character,
        health=resources["current_health"],
        max_health=resources["max_health"],
        stamina=resources["current_stamina"],
        max_stamina=resources["max_stamina"],
        tech_power=resources["current_tech_power"],
        max_tech_power=resources["max_tech_power"],
        armor=resources["current_armor"],
        max_armor=resources["max_armor"],
        is_incapacitated=resources["is_incapacitated"],
        status_message=status_message,
    )


async def get_npc_combat_status(
    ctx: RunContext[GMAgentDependencies],
    npc_id: str,
) -> ResponseCombatStatus:
    """Get the current combat resource status for an NPC.

    Args:
        ctx: The context of the agent.
        npc_id: The NPC ID to get status for.

    Returns:
        ResponseCombatStatus: The NPC's current combat status.
    """
    postgres_manager = ctx.deps.postgres_manager
    npc_repository = NPCRepository(postgres_manager)

    npc = await npc_repository.get_by_id(UUID(npc_id))
    if not npc:
        raise ValueError(f"NPC {npc_id} not found")

    # Format response
    from ds_common.combat import format_combat_status, format_resource_display

    resources = format_resource_display(npc)
    status_message = format_combat_status(npc)

    # Create a Character-like object for response
    from ds_common.models.character import Character

    npc_character = Character(
        id=npc.id,
        name=npc.name,
        current_health=npc.current_health,
        max_health=npc.max_health,
        current_stamina=npc.current_stamina,
        max_stamina=npc.max_stamina,
        current_tech_power=npc.current_tech_power,
        max_tech_power=npc.max_tech_power,
        current_armor=npc.current_armor,
        max_armor=npc.max_armor,
        is_incapacitated=npc.is_incapacitated,
    )

    return ResponseCombatStatus(
        character=npc_character,
        health=resources["current_health"],
        max_health=resources["max_health"],
        stamina=resources["current_stamina"],
        max_stamina=resources["max_stamina"],
        tech_power=resources["current_tech_power"],
        max_tech_power=resources["max_tech_power"],
        armor=resources["current_armor"],
        max_armor=resources["max_armor"],
        is_incapacitated=resources["is_incapacitated"],
        status_message=status_message,
    )


async def update_character_armor(
    ctx: RunContext[GMAgentDependencies],
    character: Character,
    armor_amount: float,
) -> ResponseCombatStatus:
    """Update a character's armor. Can be positive (restore) or negative (damage).

    Args:
        ctx: The context of the agent.
        character: The character to update armor for.
        armor_amount: Amount to change armor by (positive = restore, negative = damage).

    Returns:
        ResponseCombatStatus: The character's updated combat status.
    """
    action_character = ctx.deps.action_character
    if not action_character:
        action_character = character
    if not action_character:
        raise ValueError("No character available")

    postgres_manager = ctx.deps.postgres_manager
    character_repository = CharacterRepository(postgres_manager)
    character = await character_repository.get_by_id(action_character.id)

    if not character:
        raise ValueError("Character not found")

    # Update armor
    result = update_armor(character, armor_amount)
    await character_repository.update(character)

    # Format response
    from ds_common.combat import format_resource_display

    resources = format_resource_display(character)

    print(f"!!! Updated armor: {armor_amount} for {character.name}")

    return ResponseCombatStatus(
        character=character,
        health=resources["current_health"],
        max_health=resources["max_health"],
        stamina=resources["current_stamina"],
        max_stamina=resources["max_stamina"],
        tech_power=resources["current_tech_power"],
        max_tech_power=resources["max_tech_power"],
        armor=resources["current_armor"],
        max_armor=resources["max_armor"],
        is_incapacitated=resources["is_incapacitated"],
        status_message=result.message,
    )

