"""
Equipment system for calculating item effects on characters.
"""

from ds_common.equipment.effect_calculator import (
    calculate_damage_bonuses,
    calculate_damage_multipliers,
    calculate_healing_bonuses,
    calculate_resource_bonuses,
    calculate_stat_bonuses,
    calculate_stat_multipliers,
    get_inventory_slots_bonus,
)

__all__ = [
    "calculate_damage_bonuses",
    "calculate_damage_multipliers",
    "calculate_healing_bonuses",
    "calculate_resource_bonuses",
    "calculate_stat_bonuses",
    "calculate_stat_multipliers",
    "get_inventory_slots_bonus",
]
