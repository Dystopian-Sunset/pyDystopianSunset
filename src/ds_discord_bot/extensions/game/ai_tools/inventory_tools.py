"""
Inventory-related AI tools for managing character inventory and equipment.
"""

import uuid

from pydantic_ai import RunContext

from ds_common.combat.cooldown_service import CooldownService
from ds_common.memory.game_time_service import GameTimeService
from ds_common.memory.item_collection_service import ItemCollectionService
from ds_common.models.game_master import (
    GMAgentDependencies,
    RequestAddItem,
    RequestFindAndCollectWorldItem,
    RequestGetEquipment,
    RequestGetInventory,
    RequestRemoveEquipment,
    RequestRemoveItem,
    RequestSwapEquipment,
    ResponseEquipment,
    ResponseFindAndCollectWorldItem,
    ResponseInventory,
)
from ds_common.repository.character import CharacterRepository
from ds_common.repository.item_template import ItemTemplateRepository
from ds_common.repository.world_item import WorldItemRepository

from .base import get_character_from_context


async def get_character_inventory(
    ctx: RunContext[GMAgentDependencies],
    request: RequestGetInventory,
) -> ResponseInventory:
    """
    🔒 **MANDATORY INVENTORY CHECK - CALL THIS BEFORE ANY ITEM ACTION** 🔒

    ================================================================================
    WHEN TO CALL THIS TOOL (MANDATORY):
    ================================================================================

    You MUST call this tool BEFORE allowing any action if the player message contains:

    ✅ Action verbs: "use", "deploy", "activate", "detonate", "fire", "throw", "equip", "wield"
    ✅ Item keywords: "item", "weapon", "tool", "device", "bomb", "warhead", "equipment", "gear"
    ✅ ANY reference to using, interacting with, or manipulating an object

    ================================================================================
    WORKFLOW:
    ================================================================================

    STEP 1: Player says "use my bomb" or "deploy the warhead" or similar
    STEP 2: CALL THIS TOOL FIRST to get current inventory
    STEP 3: Check if the item exists in the returned inventory list
    STEP 4A: If item exists → Allow the action, proceed with narrative
    STEP 4B: If item does NOT exist → Reject the action narratively

    ================================================================================
    CRITICAL RULE:
    ================================================================================

    **NEVER ASSUME A PLAYER HAS AN ITEM**

    Even if the player says "use my bomb", you MUST verify they actually have it.
    The inventory shown in context may be outdated - always call this tool to get current inventory.

    Args:
        ctx: The context of the agent.
        request: The request to get the character's inventory.

    Returns:
        ResponseInventory: The character's current inventory as a list of items.
    """
    character = get_character_from_context(ctx, request)
    postgres_manager = ctx.deps.postgres_manager

    character_repository = CharacterRepository(postgres_manager)
    character = await character_repository.get_by_id(character.id)

    if not character:
        raise ValueError("Character not found")

    inventory = character.inventory if character.inventory else []

    print(f"!!! Character inventory: {inventory}")

    return ResponseInventory(
        character=character,
        inventory=inventory,
    )


async def add_character_item(
    ctx: RunContext[GMAgentDependencies],
    request: RequestAddItem,
) -> ResponseInventory:
    """
    ⚠️ **MANDATORY TOOL - YOU MUST CALL THIS WHENEVER A CHARACTER ACQUIRES ANY ITEM** ⚠️

    **THIS IS NOT OPTIONAL - IF YOU DESCRIBE ITEM ACQUISITION, YOU MUST CALL THIS TOOL**

    Args:
        ctx: The context of the agent.
        request: The request to add an item to the character's inventory.

    Returns:
        ResponseInventory: The updated character inventory.
    """
    character = get_character_from_context(ctx, request)
    postgres_manager = ctx.deps.postgres_manager

    character_repository = CharacterRepository(postgres_manager)
    character = await character_repository.get_by_id(character.id)

    if not character:
        raise ValueError(f"Character {character.id} not found")

    inventory = character.inventory if character.inventory else []

    # Try to find item template by name if available
    template_repo = ItemTemplateRepository(postgres_manager)
    template = await template_repo.get_by_field("name", request.item_name, case_sensitive=False)

    # Add the item to inventory
    if template:
        # Create item instance from template
        instance_id = str(uuid.uuid4())
        item_entry = {
            "instance_id": instance_id,
            "item_template_id": str(template.id),
            "name": template.name,
            "quantity": request.item_quantity,
            "type": request.item_type,
            "equipped": False,
            "equipment_slot": None,
        }
    else:
        # Fallback to simple item entry (backward compatibility)
        item_entry = {
            "name": request.item_name,
            "quantity": request.item_quantity,
            "type": request.item_type,
        }

    # Check if item already exists and update quantity, or add new entry
    item_found = False
    for item in inventory:
        if item.get("name") == request.item_name:
            item["quantity"] = item.get("quantity", 0) + request.item_quantity
            item_found = True
            break

    if not item_found:
        inventory.append(item_entry)

    character.inventory = inventory
    await character_repository.update(character)

    print(f"!!! Added item: {request.item_name} x{request.item_quantity} to inventory")

    return ResponseInventory(
        character=character,
        inventory=inventory,
    )


async def remove_character_item(
    ctx: RunContext[GMAgentDependencies],
    request: RequestRemoveItem,
) -> ResponseInventory:
    """
    Remove an item from a character's inventory. Use this when a player consumes, sells, drops,
    breaks, or turns in an item for a quest.

    Args:
        ctx: The context of the agent.
        request: The request to remove an item from the character's inventory.

    Returns:
        ResponseInventory: The updated character inventory.
    """
    character = get_character_from_context(ctx, request)
    postgres_manager = ctx.deps.postgres_manager

    character_repository = CharacterRepository(postgres_manager)
    character = await character_repository.get_by_id(character.id)

    if not character:
        raise ValueError(f"Character {character.id} not found")

    inventory = character.inventory if character.inventory else []

    # Find and remove/update the item
    updated_inventory = []
    item_found = False

    removed_item = None
    for item in inventory:
        if item.get("name") == request.item_name:
            item_found = True
            removed_item = item.copy()  # Save copy for cooldown logic
            current_quantity = item.get("quantity", 0)
            new_quantity = current_quantity - request.item_quantity

            if new_quantity > 0:
                item["quantity"] = new_quantity
                updated_inventory.append(item)
            # If quantity becomes 0 or less, don't add it back (item removed)
        else:
            updated_inventory.append(item)

    if not item_found:
        raise ValueError(f"Item '{request.item_name}' not found in character inventory")

    character.inventory = updated_inventory

    # Handle cooldowns based on removal reason
    cooldown_service = CooldownService(postgres_manager)

    # Check if item is being used (not sold/dropped)
    is_usage = request.item_type == "consumed"

    if removed_item and is_usage:
        # Item is being used - check for cooldown and start it if needed
        cooldown_hours = removed_item.get("cooldown_game_hours")
        if cooldown_hours and cooldown_hours > 0:
            # Determine cooldown name (prefer instance_id, fallback to item name)
            cooldown_name = removed_item.get("instance_id") or request.item_name
            await cooldown_service.start_cooldown(
                character, "ITEM", cooldown_name, float(cooldown_hours)
            )
            print(f"!!! Started cooldown for {cooldown_name}: {cooldown_hours} game hours")
    elif removed_item:
        # Item is being sold/dropped/removed - clean up cooldowns
        instance_id = removed_item.get("instance_id")
        if instance_id:
            # Remove cooldown for specific instance
            await cooldown_service.remove_item_cooldowns(character, instance_id)
        else:
            # Remove cooldowns by item name
            await cooldown_service.remove_item_cooldowns_by_name(character, request.item_name)

    await character_repository.update(character)

    print(f"!!! Removed item: {request.item_name} x{request.item_quantity} from inventory")

    return ResponseInventory(
        character=character,
        inventory=updated_inventory,
    )


async def find_and_collect_world_item(
    ctx: RunContext[GMAgentDependencies],
    request: RequestFindAndCollectWorldItem,
) -> ResponseFindAndCollectWorldItem:
    """
    🔍 **FIND AND COLLECT WORLD ITEM - USE THIS FIRST FOR ENVIRONMENTAL ITEMS** 🔍

    Use this tool when a player wants to pick up an item mentioned in the environment.
    This tool checks if the item exists as a WorldItem and collects it if found.

    Args:
        ctx: The context of the agent.
        request: The request to find and collect a world item.

    Returns:
        ResponseFindAndCollectWorldItem: Information about whether the item was found and collected.
    """
    character = get_character_from_context(ctx, request)
    postgres_manager = ctx.deps.postgres_manager

    character_repository = CharacterRepository(postgres_manager)
    character = await character_repository.get_by_id(character.id)

    if not character:
        raise ValueError("Character not found")

    # Get current character location if provided
    character_location = request.character_location or character.location

    # Search for available world items by name (case-insensitive)
    item_repo = WorldItemRepository(postgres_manager)
    available_items = await item_repo.get_available()

    # Find matching item (case-insensitive, partial match)
    matching_item = None
    item_name_lower = request.item_name.lower()
    for item in available_items:
        if item_name_lower in item.name.lower() or item.name.lower() in item_name_lower:
            # If location is specified, check if item is available at that location
            if character_location and item.regional_availability:
                locations = item.regional_availability.get("locations", [])
                regions = item.regional_availability.get("regions", [])
                # Check if character location matches item's available locations
                if character_location in locations or any(
                    region.lower() in character_location.lower() for region in regions
                ):
                    matching_item = item
                    break
            else:
                # No location restriction or location not specified, match by name
                matching_item = item
                break

    if not matching_item:
        # Item not found as a world item
        inventory = character.inventory if character.inventory else []
        return ResponseFindAndCollectWorldItem(
            character=character,
            item_name=request.item_name,
            found=False,
            collected=False,
            inventory=inventory,
            message=f"No available world item named '{request.item_name}' found in the environment.",
        )

    # Item found, try to collect it
    try:
        game_time_service = GameTimeService(postgres_manager)
        collection_service = ItemCollectionService(postgres_manager, game_time_service)

        # Check collection conditions
        if not await collection_service.check_collection_conditions(
            matching_item, character.id
        ):
            inventory = character.inventory if character.inventory else []
            return ResponseFindAndCollectWorldItem(
                character=character,
                item_name=request.item_name,
                found=True,
                collected=False,
                inventory=inventory,
                message=f"Found '{matching_item.name}' but collection conditions are not met.",
            )

        # Collect the item (marks it as collected in the world)
        collected_item = await collection_service.collect_item(
            matching_item,
            character.id,
            ctx.deps.game_session.id,
        )

        # Add item to character inventory
        template_repo = ItemTemplateRepository(postgres_manager)
        template = await template_repo.get_by_field(
            "name", collected_item.name, case_sensitive=False
        )

        inventory = character.inventory if character.inventory else []

        if template:
            # Create item instance from template
            instance_id = str(uuid.uuid4())
            item_entry = {
                "instance_id": instance_id,
                "item_template_id": str(template.id),
                "name": template.name,
                "quantity": 1,
                "equipped": False,
                "equipment_slot": None,
            }
        else:
            # Fallback to simple item entry
            item_entry = {
                "name": collected_item.name,
                "quantity": 1,
                "type": "found",
            }

        # Check if item already exists and update quantity, or add new entry
        item_found = False
        for item in inventory:
            if item.get("name") == collected_item.name:
                item["quantity"] = item.get("quantity", 0) + 1
                item_found = True
                break

        if not item_found:
            inventory.append(item_entry)

        character.inventory = inventory
        await character_repository.update(character)

        print(f"!!! Collected world item: {collected_item.name} and added to inventory")

        return ResponseFindAndCollectWorldItem(
            character=character,
            item_name=collected_item.name,
            found=True,
            collected=True,
            inventory=inventory,
            message=f"Successfully collected '{collected_item.name}' and added it to your inventory.",
        )

    except ValueError as e:
        # Collection failed (e.g., already collected, conditions not met)
        inventory = character.inventory if character.inventory else []
        return ResponseFindAndCollectWorldItem(
            character=character,
            item_name=request.item_name,
            found=True,
            collected=False,
            inventory=inventory,
            message=f"Found '{matching_item.name}' but could not collect it: {e!s}",
        )


async def get_equipped_items(
    ctx: RunContext[GMAgentDependencies],
    request: RequestGetEquipment,
) -> ResponseEquipment:
    """
    Get all equipped items for a character.

    Args:
        ctx: The context of the agent.
        request: The request to get equipped items.

    Returns:
        ResponseEquipment: The character's equipped items.
    """
    character = get_character_from_context(ctx, request)
    postgres_manager = ctx.deps.postgres_manager

    character_repository = CharacterRepository(postgres_manager)
    character = await character_repository.get_by_id(character.id)

    if not character:
        raise ValueError("Character not found")

    equipped = await character_repository.get_equipped_items(character)

    print(f"!!! Got equipped items for {character.name}: {equipped}")

    return ResponseEquipment(
        character=character,
        equipment=list(equipped.values()),
    )


async def equip_item(
    ctx: RunContext[GMAgentDependencies],
    request: RequestSwapEquipment,
) -> ResponseInventory:
    """
    Equip an item from inventory to a slot.

    Args:
        ctx: The context of the agent.
        request: The request to equip an item.

    Returns:
        ResponseInventory: The updated character inventory.
    """
    character = get_character_from_context(ctx, request)
    postgres_manager = ctx.deps.postgres_manager

    character_repository = CharacterRepository(postgres_manager)
    character = await character_repository.get_by_id(character.id)

    if not character:
        raise ValueError("Character not found")

    # Find item by name in inventory
    inventory = character.inventory or []
    item_instance_id = None
    for item in inventory:
        if isinstance(item, dict) and item.get("name") == request.item_name:
            item_instance_id = item.get("instance_id")
            if not item_instance_id:
                # Generate instance_id if missing
                item_instance_id = str(uuid.uuid4())
                item["instance_id"] = item_instance_id
            break

    if not item_instance_id:
        raise ValueError(f"Item '{request.item_name}' not found in inventory")

    # Equip the item
    character = await character_repository.equip_item(
        character, item_instance_id, request.location
    )

    print(f"!!! Equipped {request.item_name} to {request.location} for {character.name}")

    return ResponseInventory(
        character=character,
        inventory=character.inventory or [],
    )


async def unequip_item(
    ctx: RunContext[GMAgentDependencies],
    request: RequestRemoveEquipment,
) -> ResponseInventory:
    """
    Unequip an item from a slot.

    Args:
        ctx: The context of the agent.
        request: The request to unequip an item.

    Returns:
        ResponseInventory: The updated character inventory.
    """
    character = get_character_from_context(ctx, request)
    postgres_manager = ctx.deps.postgres_manager

    character_repository = CharacterRepository(postgres_manager)
    character = await character_repository.get_by_id(character.id)

    if not character:
        raise ValueError("Character not found")

    # Unequip the item
    character = await character_repository.unequip_item(character, request.location)

    print(f"!!! Unequipped item from {request.location} for {character.name}")

    return ResponseInventory(
        character=character,
        inventory=character.inventory or [],
    )

