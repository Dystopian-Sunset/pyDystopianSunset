"""
Resource calculation service for calculating max resources from stats.
"""

from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from ds_common.models.character import Character
    from ds_common.models.character_class import CharacterClass
    from ds_common.models.npc import NPC

# Character class IDs from seed data
ENFORCER_ID = UUID("00000000-0000-0000-0000-000000000001")
TECH_WIZARD_ID = UUID("00000000-0000-0000-0000-000000000002")
SMOOTH_TALKER_ID = UUID("00000000-0000-0000-0000-000000000003")
SPY_ID = UUID("00000000-0000-0000-0000-000000000004")
WILD_CARD_ID = UUID("00000000-0000-0000-0000-000000000005")


def _get_class_modifiers(character_class_id: UUID | None, level: int) -> dict[str, float]:
    """
    Get class-specific modifiers for resource calculations.

    Args:
        character_class_id: Character class UUID
        level: Character level

    Returns:
        Dictionary with health, stamina, tech_power, and armor modifiers
    """
    if character_class_id == ENFORCER_ID:
        return {
            "health_base": 50.0,
            "health_per_level": 5.0,
            "stamina_base": 30.0,
            "stamina_per_level": 0.0,
            "tech_power_base": 10.0,
            "tech_power_per_level": 0.0,
            "armor_base": 0.0,
            "armor_per_level": 0.0,
        }
    if character_class_id == TECH_WIZARD_ID:
        return {
            "health_base": 20.0,
            "health_per_level": 0.0,
            "stamina_base": 15.0,
            "stamina_per_level": 0.0,
            "tech_power_base": 50.0,
            "tech_power_per_level": 10.0,
            "armor_base": 0.0,
            "armor_per_level": 0.0,
        }
    if character_class_id == SMOOTH_TALKER_ID:
        return {
            "health_base": 30.0,
            "health_per_level": 0.0,
            "stamina_base": 20.0,
            "stamina_per_level": 0.0,
            "tech_power_base": 30.0,
            "tech_power_per_level": 0.0,
            "armor_base": 0.0,
            "armor_per_level": 0.0,
        }
    if character_class_id == SPY_ID:
        return {
            "health_base": 25.0,
            "health_per_level": 0.0,
            "stamina_base": 40.0,
            "stamina_per_level": 0.0,
            "tech_power_base": 25.0,
            "tech_power_per_level": 0.0,
            "armor_base": 0.0,
            "armor_per_level": 0.0,
        }
    if character_class_id == WILD_CARD_ID:
        return {
            "health_base": 35.0,
            "health_per_level": 0.0,
            "stamina_base": 25.0,
            "stamina_per_level": 0.0,
            "tech_power_base": 35.0,
            "tech_power_per_level": 0.0,
            "armor_base": 0.0,
            "armor_per_level": 0.0,
        }
    # Default/no class
    return {
        "health_base": 0.0,
        "health_per_level": 0.0,
        "stamina_base": 0.0,
        "stamina_per_level": 0.0,
        "tech_power_base": 0.0,
        "tech_power_per_level": 0.0,
        "armor_base": 0.0,
        "armor_per_level": 0.0,
    }


def calculate_max_health(
    character: "Character | NPC",
    character_class: "CharacterClass | None" = None,
    equipment_resource_bonuses: dict[str, float] | None = None,
) -> float:
    """
    Calculate maximum health from character stats, class, and equipment.

    Formula: (STR * 8) + (DEX * 2) + (level * 10) + class_modifier + equipment_bonus

    Args:
        character: Character or NPC instance
        character_class: Optional character class (for characters)
        equipment_resource_bonuses: Optional dict of equipment resource bonuses

    Returns:
        Maximum health as float
    """
    stats = character.stats
    str_val = float(stats.get("STR", 0))
    dex_val = float(stats.get("DEX", 0))
    level = float(character.level)

    class_id = character.character_class_id if hasattr(character, "character_class_id") else None
    modifiers = _get_class_modifiers(class_id, character.level)

    base_health = (str_val * 8.0) + (dex_val * 2.0) + (level * 10.0)
    class_bonus = modifiers["health_base"] + (modifiers["health_per_level"] * level)
    equipment_bonus = (
        float(equipment_resource_bonuses.get("max_health", 0.0))
        if equipment_resource_bonuses
        else 0.0
    )

    return base_health + class_bonus + equipment_bonus


def calculate_max_stamina(
    character: "Character | NPC",
    character_class: "CharacterClass | None" = None,
    equipment_resource_bonuses: dict[str, float] | None = None,
) -> float:
    """
    Calculate maximum stamina from character stats, class, and equipment.

    Formula: (DEX * 5) + (STR * 2) + (level * 5) + class_modifier + equipment_bonus

    Args:
        character: Character or NPC instance
        character_class: Optional character class (for characters)
        equipment_resource_bonuses: Optional dict of equipment resource bonuses

    Returns:
        Maximum stamina as float
    """
    stats = character.stats
    dex_val = float(stats.get("DEX", 0))
    str_val = float(stats.get("STR", 0))
    level = float(character.level)

    class_id = character.character_class_id if hasattr(character, "character_class_id") else None
    modifiers = _get_class_modifiers(class_id, character.level)

    base_stamina = (dex_val * 5.0) + (str_val * 2.0) + (level * 5.0)
    class_bonus = modifiers["stamina_base"] + (modifiers["stamina_per_level"] * level)
    equipment_bonus = (
        float(equipment_resource_bonuses.get("max_stamina", 0.0))
        if equipment_resource_bonuses
        else 0.0
    )

    return base_stamina + class_bonus + equipment_bonus


def calculate_max_tech_power(
    character: "Character | NPC",
    character_class: "CharacterClass | None" = None,
    equipment_resource_bonuses: dict[str, float] | None = None,
) -> float:
    """
    Calculate maximum tech power from character stats, class, and equipment.

    Formula: (INT * 10) + (level * 8) + class_modifier + equipment_bonus

    Args:
        character: Character or NPC instance
        character_class: Optional character class (for characters)
        equipment_resource_bonuses: Optional dict of equipment resource bonuses

    Returns:
        Maximum tech power as float
    """
    stats = character.stats
    int_val = float(stats.get("INT", 0))
    level = float(character.level)

    class_id = character.character_class_id if hasattr(character, "character_class_id") else None
    modifiers = _get_class_modifiers(class_id, character.level)

    base_tech_power = (int_val * 10.0) + (level * 8.0)
    class_bonus = modifiers["tech_power_base"] + (modifiers["tech_power_per_level"] * level)
    equipment_bonus = (
        float(equipment_resource_bonuses.get("max_tech_power", 0.0))
        if equipment_resource_bonuses
        else 0.0
    )

    return base_tech_power + class_bonus + equipment_bonus


def calculate_max_armor(
    character: "Character | NPC",
    character_class: "CharacterClass | None" = None,
    equipment_resource_bonuses: dict[str, float] | None = None,
) -> float:
    """
    Calculate maximum armor from character stats and equipment.

    Formula: (DEX * 3) + equipment_bonus + (level * 2)

    Args:
        character: Character or NPC instance
        character_class: Optional character class (for characters)
        equipment_resource_bonuses: Optional dict of equipment resource bonuses

    Returns:
        Maximum armor as float
    """
    stats = character.stats
    dex_val = float(stats.get("DEX", 0))
    level = float(character.level)

    # Base armor calculation
    base_armor = (dex_val * 3.0) + (level * 2.0)

    # Equipment bonus from equipped items
    equipment_bonus = (
        float(equipment_resource_bonuses.get("max_armor", 0.0))
        if equipment_resource_bonuses
        else 0.0
    )

    return base_armor + equipment_bonus
