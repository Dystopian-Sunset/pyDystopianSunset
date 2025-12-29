"""
Tool creation for AI agent.

This module provides the function to create and return all agent tools.
"""


def create_tools():
    """
    Create and return all agent tools.
    Tools are defined as regular functions and will be passed to the Agent constructor.
    """
    # Import all tools from the ai_tools package
    from .ai_tools import (
        # Character tools
        adjust_character_credits,
        get_character_credits,
        update_character_location,
        # Quest tools
        add_character_quest,
        get_character_quests,
        remove_character_quest,
        # Inventory tools
        add_character_item,
        equip_item,
        find_and_collect_world_item,
        get_character_inventory,
        get_equipped_items,
        remove_character_item,
        unequip_item,
        # Combat tools
        apply_character_damage,
        apply_character_healing,
        apply_npc_damage,
        apply_npc_healing,
        consume_character_resource,
        get_character_combat_status,
        get_npc_combat_status,
        restore_character_resource,
        update_character_armor,
        # Encounter tools
        start_encounter,
        end_encounter,
        get_encounter_status,
        abandon_encounter,
        add_character_to_encounter,
        remove_character_from_encounter,
        add_npc_to_encounter,
        remove_npc_from_encounter,
        distribute_encounter_rewards,
        search_corpse,
        # World tools
        create_location_edge,
        create_location_node,
        fetch_npc,
        # Cooldown tools
        check_character_cooldown,
        get_character_cooldowns,
        start_character_cooldown,
    )

    # Return all tools as a list
    return [
        fetch_npc,
        get_character_credits,
        adjust_character_credits,
        add_character_quest,
        get_character_quests,
        remove_character_quest,
        get_character_inventory,
        add_character_item,
        remove_character_item,
        find_and_collect_world_item,
        get_equipped_items,
        equip_item,
        unequip_item,
        apply_character_damage,
        apply_character_healing,
        apply_npc_damage,
        apply_npc_healing,
        consume_character_resource,
        restore_character_resource,
        get_character_combat_status,
        get_npc_combat_status,
        update_character_armor,
        start_encounter,
        end_encounter,
        get_encounter_status,
        abandon_encounter,
        add_character_to_encounter,
        remove_character_from_encounter,
        add_npc_to_encounter,
        remove_npc_from_encounter,
        distribute_encounter_rewards,
        search_corpse,
        create_location_node,
        create_location_edge,
        update_character_location,
        check_character_cooldown,
        get_character_cooldowns,
        start_character_cooldown,
    ]
