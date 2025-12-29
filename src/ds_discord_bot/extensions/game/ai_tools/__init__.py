"""
AI tools package for game extension.

Exports all tool functions for use in _create_tools().
"""

from .character_tools import (
    adjust_character_credits,
    get_character_credits,
    update_character_location,
)
from .cooldown_tools import (
    check_character_cooldown,
    get_character_cooldowns,
    start_character_cooldown,
)
from .combat_tools import (
    apply_character_damage,
    apply_character_healing,
    apply_npc_damage,
    apply_npc_healing,
    consume_character_resource,
    get_character_combat_status,
    get_npc_combat_status,
    restore_character_resource,
    update_character_armor,
)
from .encounter_tools import (
    abandon_encounter,
    add_character_to_encounter,
    add_npc_to_encounter,
    distribute_encounter_rewards,
    end_encounter,
    get_encounter_status,
    remove_character_from_encounter,
    remove_npc_from_encounter,
    search_corpse,
    start_encounter,
)
from .inventory_tools import (
    add_character_item,
    equip_item,
    find_and_collect_world_item,
    get_character_inventory,
    get_equipped_items,
    remove_character_item,
    unequip_item,
)
from .quest_tools import (
    add_character_quest,
    get_character_quests,
    remove_character_quest,
)
from .world_tools import (
    create_location_edge,
    create_location_node,
    fetch_npc,
)

__all__ = [
    # Character tools
    "get_character_credits",
    "adjust_character_credits",
    "update_character_location",
    # Quest tools
    "add_character_quest",
    "get_character_quests",
    "remove_character_quest",
    # Inventory tools
    "get_character_inventory",
    "add_character_item",
    "remove_character_item",
    "find_and_collect_world_item",
    "get_equipped_items",
    "equip_item",
    "unequip_item",
    # Combat tools
    "apply_character_damage",
    "apply_character_healing",
    "apply_npc_damage",
    "apply_npc_healing",
    "consume_character_resource",
    "restore_character_resource",
    "get_character_combat_status",
    "get_npc_combat_status",
    "update_character_armor",
    # Encounter tools
    "start_encounter",
    "end_encounter",
    "get_encounter_status",
    "abandon_encounter",
    "add_character_to_encounter",
    "remove_character_from_encounter",
    "add_npc_to_encounter",
    "remove_npc_from_encounter",
    "distribute_encounter_rewards",
    "search_corpse",
    # World tools
    "fetch_npc",
    "create_location_node",
    "create_location_edge",
    # Cooldown tools
    "check_character_cooldown",
    "get_character_cooldowns",
    "start_character_cooldown",
]
