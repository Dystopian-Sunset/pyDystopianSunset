"""
Prompt service for loading and registering dynamic system prompts.
"""

import logging
from collections.abc import AsyncGenerator
from pathlib import Path

import aiofiles
import aiofiles.os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic_ai import Agent
    from pydantic_ai import RunContext
    from ds_common.models.game_master import GMAgentDependencies


def register_system_prompts(agent: "Agent", prompt_loader):
    """
    Register all prompt modules dynamically.

    This function creates system prompt functions for each module and registers
    them with the agent. Each function checks if the module should be loaded
    based on the context's prompt_modules set.

    Args:
        agent: The pydantic_ai Agent instance
        prompt_loader: The prompt loader instance
    """
    # We need to create separate functions for each module to avoid closure issues
    @agent.system_prompt
    async def core_identity_prompt(ctx: "RunContext[GMAgentDependencies]") -> str:
        if not ctx.deps.prompt_modules or "core_identity" not in ctx.deps.prompt_modules:
            return ""
        return await prompt_loader.load_module("core_identity") if prompt_loader else ""

    @agent.system_prompt
    async def formatting_guidelines_prompt(ctx: "RunContext[GMAgentDependencies]") -> str:
        if not ctx.deps.prompt_modules or "formatting_guidelines" not in ctx.deps.prompt_modules:
            return ""
        return await prompt_loader.load_module("formatting_guidelines") if prompt_loader else ""

    @agent.system_prompt
    async def content_guidelines_prompt(ctx: "RunContext[GMAgentDependencies]") -> str:
        if not ctx.deps.prompt_modules or "content_guidelines" not in ctx.deps.prompt_modules:
            return ""
        return await prompt_loader.load_module("content_guidelines") if prompt_loader else ""

    @agent.system_prompt
    async def inventory_rules_prompt(ctx: "RunContext[GMAgentDependencies]") -> str:
        if not ctx.deps.prompt_modules or "inventory_rules" not in ctx.deps.prompt_modules:
            return ""
        return await prompt_loader.load_module("inventory_rules") if prompt_loader else ""

    @agent.system_prompt
    async def quest_rules_prompt(ctx: "RunContext[GMAgentDependencies]") -> str:
        if not ctx.deps.prompt_modules or "quest_rules" not in ctx.deps.prompt_modules:
            return ""
        return await prompt_loader.load_module("quest_rules") if prompt_loader else ""

    @agent.system_prompt
    async def combat_rules_prompt(ctx: "RunContext[GMAgentDependencies]") -> str:
        if not ctx.deps.prompt_modules or "combat_rules" not in ctx.deps.prompt_modules:
            return ""
        return await prompt_loader.load_module("combat_rules") if prompt_loader else ""

    @agent.system_prompt
    async def travel_rules_prompt(ctx: "RunContext[GMAgentDependencies]") -> str:
        if not ctx.deps.prompt_modules or "travel_rules" not in ctx.deps.prompt_modules:
            return ""
        return await prompt_loader.load_module("travel_rules") if prompt_loader else ""

    @agent.system_prompt
    async def calendar_system_prompt(ctx: "RunContext[GMAgentDependencies]") -> str:
        if not ctx.deps.prompt_modules or "calendar_system" not in ctx.deps.prompt_modules:
            return ""
        return await prompt_loader.load_module("calendar_system") if prompt_loader else ""

    @agent.system_prompt
    async def faction_info_prompt(ctx: "RunContext[GMAgentDependencies]") -> str:
        if not ctx.deps.prompt_modules or "faction_info" not in ctx.deps.prompt_modules:
            return ""
        return await prompt_loader.load_module("faction_info") if prompt_loader else ""

    @agent.system_prompt
    async def setting_lore_prompt(ctx: "RunContext[GMAgentDependencies]") -> str:
        if not ctx.deps.prompt_modules or "setting_lore" not in ctx.deps.prompt_modules:
            return ""
        return await prompt_loader.load_module("setting_lore") if prompt_loader else ""

    @agent.system_prompt
    async def location_specific_prompt(ctx: "RunContext[GMAgentDependencies]") -> str:
        if not ctx.deps.prompt_modules or "location_specific" not in ctx.deps.prompt_modules:
            return ""
        return await prompt_loader.load_module("location_specific") if prompt_loader else ""

    @agent.system_prompt
    async def encounter_types_prompt(ctx: "RunContext[GMAgentDependencies]") -> str:
        if not ctx.deps.prompt_modules or "encounter_types" not in ctx.deps.prompt_modules:
            return ""
        return await prompt_loader.load_module("encounter_types") if prompt_loader else ""

    @agent.system_prompt
    async def narrative_guidelines_prompt(ctx: "RunContext[GMAgentDependencies]") -> str:
        if not ctx.deps.prompt_modules or "narrative_guidelines" not in ctx.deps.prompt_modules:
            return ""
        return await prompt_loader.load_module("narrative_guidelines") if prompt_loader else ""

    @agent.system_prompt
    async def world_consistency_prompt(ctx: "RunContext[GMAgentDependencies]") -> str:
        if not ctx.deps.prompt_modules or "world_consistency" not in ctx.deps.prompt_modules:
            return ""
        return await prompt_loader.load_module("world_consistency") if prompt_loader else ""


async def load_system_prompt(prompt_path: Path) -> AsyncGenerator[str]:
    """
    Load a system prompt file line by line.

    Args:
        prompt_path: Path to the prompt file

    Yields:
        Each non-empty line from the prompt file
    """
    logger = logging.getLogger(__name__)

    if not await aiofiles.os.path.isfile(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    async with aiofiles.open(prompt_path) as f:
        lines = await f.readlines()

    for line in [line.strip() for line in lines]:
        if not line:
            continue

        yield line

    logger.debug(f"Loaded prompt from {prompt_path}")


def register_user_context_prompt(agent: "Agent"):
    """
    Register the user_context system prompt for character-specific information.

    This prompt provides detailed character information including inventory,
    resources, location, pronouns, and other character-specific context.

    Args:
        agent: The pydantic_ai Agent instance
    """
    from pydantic_ai import RunContext
    from ds_common.models.game_master import GMAgentDependencies
    from ds_common.repository.character import CharacterRepository

    @agent.system_prompt
    async def user_context(ctx: RunContext[GMAgentDependencies]) -> str:
        character_repository = CharacterRepository(ctx.deps.postgres_manager)

        if ctx.deps.action_character:
            character_class = await character_repository.get_character_class(
                ctx.deps.action_character
            )

            # Get fresh character data to ensure inventory is up to date
            # CRITICAL: Always fetch from database with a fresh session to avoid caching issues
            # Use read_only=False to ensure we get the latest committed data (not from a read replica that might lag)
            character = await character_repository.get_by_id(
                ctx.deps.action_character.id, read_only=False
            )
            if not character:
                # Fallback to context character if database fetch fails
                character = ctx.deps.action_character
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"user_context: Failed to fetch character {ctx.deps.action_character.id} from database, using context character"
                )

            # Get inventory - handle both list and None cases
            # SQLModel should deserialize JSON automatically, but ensure we handle edge cases
            inventory = character.inventory if character.inventory else []

            # Log inventory state for debugging (debug level only - empty inventory is valid)
            logger = logging.getLogger(__name__)
            if inventory:
                logger.debug(
                    f"user_context: Character {character.name} inventory has {len(inventory)} items: "
                    f"{[item.get('name', 'Unknown') if isinstance(item, dict) else str(item) for item in inventory[:3]]}"
                )
            else:
                logger.debug(
                    f"user_context: Character {character.name} has empty inventory (this is valid)"
                )

            # Format inventory for better readability with explicit item names list
            if inventory:
                inventory_lines = []
                equipped_items_list = []
                unequipped_items_list = []
                all_item_names = []  # Track all item names for explicit listing

                for item in inventory:
                    if isinstance(item, dict):
                        name = item.get("name", "Unknown Item")
                        quantity = item.get("quantity", 1)
                        equipped = item.get("equipped", False)
                        slot = item.get("equipment_slot")

                        # Add to explicit names list
                        for _ in range(quantity):
                            all_item_names.append(name)

                        item_display = f"{name}"
                        if quantity > 1:
                            item_display += f" x{quantity}"

                        if equipped and slot:
                            equipped_items_list.append(
                                f"  - {item_display} (Equipped, {slot.replace('_', ' ').title()})"
                            )
                        else:
                            unequipped_items_list.append(f"  - {item_display}")

                inventory_parts = []
                if equipped_items_list:
                    inventory_parts.append("Equipped Items:")
                    inventory_parts.extend(equipped_items_list)
                if unequipped_items_list:
                    if equipped_items_list:
                        inventory_parts.append("")  # Blank line separator
                    inventory_parts.append("Unequipped Items:")
                    inventory_parts.extend(unequipped_items_list)

                # Create explicit item names list for clarity
                item_names_list = ", ".join(sorted(set(all_item_names)))
                inventory_info = f"""**CHARACTER INVENTORY - EXACT ITEMS THE CHARACTER POSSESSES:**

{item_names_list}

Detailed Inventory:
{chr(10).join(inventory_parts)}

**CRITICAL: The character ONLY has the items listed above. DO NOT mention any other items in narrative descriptions.**"""
            else:
                inventory_info = """**CHARACTER INVENTORY - EXACT ITEMS THE CHARACTER POSSESSES:**

(empty - character has no items)

**CRITICAL: The character has NO items. DO NOT mention any items in narrative descriptions.**"""

            # Get character credits/funds
            credits_info = f"Credits: {character.credits} quill"

            # Get character resources
            from ds_common.combat.display import format_resource_display

            resources = format_resource_display(character)
            resources_info = (
                f"Health: {resources['current_health']}/{resources['max_health']} | "
                f"Stamina: {resources['current_stamina']}/{resources['max_stamina']} | "
                f"Tech Power: {resources['current_tech_power']}/{resources['max_tech_power']} | "
                f"Armor: {resources['current_armor']}/{resources['max_armor']} | "
                f"Credits: {character.credits} quill"
            )

            # Get active cooldowns
            from ds_common.combat.cooldown_service import CooldownService

            cooldown_service = CooldownService(ctx.deps.postgres_manager)
            # Cleanup orphaned cooldowns first
            await cooldown_service.cleanup_orphaned_cooldowns(character)
            # Cleanup expired cooldowns
            await cooldown_service.cleanup_expired_cooldowns(character)
            # Get active cooldowns
            active_cooldowns = await cooldown_service.get_active_cooldowns(character)
            cooldowns_info = ""
            if active_cooldowns:
                cooldown_parts = []
                for cooldown in active_cooldowns:
                    remaining = await cooldown_service.get_cooldown_remaining(
                        character, cooldown.cooldown_type, cooldown.cooldown_name
                    )
                    if remaining is not None:
                        cooldown_parts.append(
                            f"{cooldown.cooldown_name} ({cooldown.cooldown_type}): {remaining:.2f} game hours"
                        )
                if cooldown_parts:
                    cooldowns_info = f"\nActive Cooldowns: {', '.join(cooldown_parts)}"
            else:
                cooldowns_info = "\nActive Cooldowns: None"

            # Add resource warnings
            resource_warnings = ""
            if resources["current_health"] < resources["max_health"] * 0.25:
                resource_warnings += (
                    "\n⚠️ WARNING: Character health is below 25% - they are in critical condition."
                )
            if resources["is_incapacitated"]:
                resource_warnings += (
                    "\n🚨 CRITICAL: Character is INCAPACITATED - they cannot take actions."
                )
            if resources["current_stamina"] < resources["max_stamina"] * 0.2:
                resource_warnings += (
                    "\n⚠️ WARNING: Character stamina is very low - physical actions may fail."
                )
            if resources["current_tech_power"] < resources["max_tech_power"] * 0.2:
                resource_warnings += (
                    "\n⚠️ WARNING: Character tech power is very low - tech actions may fail."
                )

            # Get game time
            game_time_info = ""
            try:
                from ds_common.memory.game_time_service import GameTimeService

                game_time_service = GameTimeService(ctx.deps.postgres_manager)
                game_time = await game_time_service.get_current_game_time()
                time_of_day = await game_time_service.get_time_of_day()
                month_name = await game_time_service.get_current_month_name()
                cycle_animal = await game_time_service.get_current_cycle_animal()

                month_display = f", Month: {month_name}" if month_name else ""
                cycle_display = f" ({cycle_animal} Year)" if cycle_animal else ""
                year_day = (
                    game_time.year_day
                    if hasattr(game_time, "year_day") and game_time.year_day
                    else game_time.game_day
                )
                game_day = (
                    game_time.game_day
                    if hasattr(game_time, "game_day") and game_time.game_day
                    else None
                )

                day_display = f"Day {game_day}" if game_day else f"Year Day {year_day}"
                game_time_info = (
                    f"\nGame Time: Year {game_time.game_year}{cycle_display}{month_display}, {day_display}, "
                    f"Hour {game_time.game_hour:02d}:{game_time.game_minute:02d}, "
                    f"Season: {game_time.season}, {time_of_day.title()}, "
                    f"{'Daytime' if game_time.is_daytime else 'Nighttime'}"
                )
            except Exception:
                # Game time unavailable, skip
                pass

            # Determine pronouns based on gender
            # Log gender for debugging
            logger = logging.getLogger(__name__)
            logger.debug(f"Character {character.name} gender: {character.gender}")

            if character.gender == "Female":
                pronouns = "she/her"
                pronoun_subject = "she"
                pronoun_object = "her"
                pronoun_possessive = "her"
            elif character.gender == "Male":
                pronouns = "he/him"
                pronoun_subject = "he"
                pronoun_object = "him"
                pronoun_possessive = "his"
            elif character.gender == "Other":
                pronouns = "they/them"
                pronoun_subject = "they"
                pronoun_object = "them"
                pronoun_possessive = "their"
            else:
                # Default to they/them if gender not set
                logger.warning(
                    f"Character {character.name} has no gender set, defaulting to they/them"
                )
                pronouns = "they/them"
                pronoun_subject = "they"
                pronoun_object = "them"
                pronoun_possessive = "their"

            gender_info = (
                f"Gender: {character.gender} ({pronouns})"
                if character.gender
                else "Gender: Not specified (use they/them pronouns)"
            )

            # Get current location with full context including parent locations
            location_info = ""
            try:
                if character.current_location:
                    from ds_common.repository.location_fact import LocationFactRepository
                    from ds_common.repository.location_node import LocationNodeRepository
                    from ds_common.repository.world_region import WorldRegionRepository

                    node_repository = LocationNodeRepository(ctx.deps.postgres_manager)
                    location_node = await node_repository.get_by_id(character.current_location)
                    if location_node:
                        location_parts = [f"{location_node.location_name}"]

                        # Add parent location if available
                        if location_node.parent_location_id:
                            parent_node = await node_repository.get_by_id(
                                location_node.parent_location_id
                            )
                            if parent_node:
                                location_parts.append(f"within {parent_node.location_name}")

                        # Try to get region/city information
                        city_name = None
                        if location_node.location_fact_id:
                            fact_repo = LocationFactRepository(ctx.deps.postgres_manager)
                            location_fact = await fact_repo.get_by_id(
                                location_node.location_fact_id
                            )
                            if location_fact and location_fact.region_id:
                                region_repo = WorldRegionRepository(ctx.deps.postgres_manager)
                                region = await region_repo.get_by_id(location_fact.region_id)
                                if region:
                                    if region.hierarchy_level == 0:  # City
                                        city_name = region.name
                                    elif region.parent_region_id:
                                        parent_region = await region_repo.get_by_id(
                                            region.parent_region_id
                                        )
                                        if parent_region and parent_region.hierarchy_level == 0:
                                            city_name = parent_region.name

                        # Fallback: check if location itself is a city
                        if not city_name and location_node.location_type == "CITY":
                            city_name = location_node.location_name

                        if city_name and city_name not in location_parts:
                            location_parts.append(f"in {city_name}")

                        location_description = " ".join(location_parts)
                        location_info = f"\n**CURRENT LOCATION: {character.name} is currently at {location_description}**\n\n**CRITICAL: Always maintain awareness of this location. When describing scenes, offering paths, or responding to player actions, the character is AT THIS LOCATION unless they have explicitly traveled elsewhere. If the location is not fully defined, reference it in relation to known locations (parent location, city, region) from the world location graph.**\n"
            except Exception as e:
                # Log error but don't fail - location info is helpful but not critical
                logger = logging.getLogger(__name__)
                logger.debug(f"Failed to get location context: {e}")

            return f"""
            **CRITICAL - CHARACTER PRONOUNS - READ THIS FIRST:**
            The player character is {character.name}. {character.name}'s gender is {character.gender if character.gender else "not specified"}.
            
            **YOU MUST USE THESE PRONOUNS FOR {character.name.upper()}:**
            - Subject: {pronoun_subject}
            - Object: {pronoun_object}
            - Possessive: {pronoun_possessive}
            
            **EXAMPLES OF CORRECT USAGE:**
            - "{pronoun_subject.capitalize()} walks into the room"
            - "The NPC gives {pronoun_object} the item"
            - "{pronoun_possessive.capitalize()} weapon glows"
            - "{character.name} steps forward. {pronoun_subject.capitalize()} looks around carefully."
            
            **VIOLATION OF THIS RULE IS A CRITICAL ERROR.** Always double-check your pronouns match the character's gender before responding.
            
            The player is playing as {character.name}.
            {gender_info}
            {location_info}
            {pronoun_subject.capitalize()} is a {character_class.name} which has a background of ({character_class.description}). 
            The player has the following stats: {character.stats}
            Resources: {resources_info}{resource_warnings}{cooldowns_info}
            {inventory_info}{game_time_info}
            
            **IMPORTANT: Character Financial Status**
            The character currently has {character.credits} quill (the standard currency). When displaying resources or answering questions about money/funds/credits/quill, always use this exact value: {character.credits} quill. Do NOT use any other currency symbol or format.
            
            **🚨🚨🚨 CRITICAL RULE - INVENTORY ACCURACY - THIS IS THE MOST IMPORTANT RULE 🚨🚨🚨**
            
            **YOU ARE FORBIDDEN FROM INVENTING OR MAKING UP ITEMS. THIS IS A CRITICAL ERROR.**
            
            **THE CHARACTER'S EXACT INVENTORY IS LISTED ABOVE. THESE ARE THE ONLY ITEMS THEY HAVE.**
            
            **WHEN DESCRIBING INVENTORY IN NARRATIVE (ESPECIALLY IN OPENING SCENES):**
            - You MUST ONLY mention items that are EXACTLY listed in the inventory above
            - DO NOT invent, create, make up, or assume any items exist
            - DO NOT add items for "narrative flavor" or "atmosphere"
            - DO NOT mention items that "would make sense" for the character class
            - If the inventory shows "Tech Jacket, Cyberdeck, Data Gloves", you can ONLY mention those three items
            - DO NOT mention items like "Hacking Deck", "Multi-Tool Kit", "Nano-drones", "Personal Data Chip", "Wire-Cab Kit" unless those EXACT names appear in the inventory list above
            - If you want to describe the character's gear, ONLY reference items from the exact list above
            
            **BEFORE WRITING ANY NARRATIVE THAT MENTIONS ITEMS:**
            1. Look at the inventory list above
            2. Identify the EXACT item names listed
            3. ONLY use those exact item names in your narrative
            4. If an item is not in the list, DO NOT mention it - the character does not have it
            
            **WHEN PLAYER USES ITEMS:**
            If the player's message contains ANY reference to using, deploying, activating, detonating, or interacting with ANY item, weapon, tool, device, bomb, warhead, or equipment, you MUST:
            1. FIRST call get_character_inventory tool to check what items they actually have
            2. Verify the required item exists in the returned inventory list
            3. ONLY if the item exists, allow the action
            4. If the item does NOT exist, you MUST reject the action and explain narratively why it fails
            
            **NEVER ASSUME A PLAYER HAS AN ITEM** - Even if they say "use my bomb", you MUST check inventory first.
            The inventory shown above is their CURRENT inventory. If an item is not listed, they don't have it.
            If you're unsure, call get_character_inventory to get the most up-to-date inventory.
            
            **VIOLATION OF THIS RULE BREAKS GAME INTEGRITY AND IS A CRITICAL ERROR.**
            **IF YOU INVENT ITEMS, YOU ARE LYING TO THE PLAYER ABOUT WHAT THEY HAVE.**"""
        return ""

