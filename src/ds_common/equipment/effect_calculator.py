"""
Equipment effect calculator for aggregating item effects on characters.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ds_common.models.character import Character
    from ds_common.models.item_template import ItemTemplate
    from ds_common.models.npc import NPC
    from ds_discord_bot.postgres_manager import PostgresManager


async def _get_equipped_item_templates(
    character: "Character | NPC",
    postgres_manager: "PostgresManager | None" = None,
) -> list["ItemTemplate"]:
    """
    Get item templates for all equipped items.

    Args:
        character: Character or NPC to check
        postgres_manager: Optional postgres manager (required if character has item_template_id)

    Returns:
        List of ItemTemplate instances for equipped items
    """
    if not hasattr(character, "inventory") or not character.inventory:
        return []

    equipped_templates = []

    if postgres_manager:
        from ds_common.repository.item_template import ItemTemplateRepository

        template_repo = ItemTemplateRepository(postgres_manager)

        for item in character.inventory:
            if not isinstance(item, dict):
                continue

            # Check if item is equipped
            is_equipped = item.get("equipped", False) or item.get("equipment_slot") is not None

            if not is_equipped:
                continue

            # Get item_template_id
            item_template_id = item.get("item_template_id")
            if item_template_id:
                try:
                    template = await template_repo.get_by_id(item_template_id)
                    if template:
                        equipped_templates.append(template)
                except Exception:
                    # Skip if template not found or error loading
                    continue

    return equipped_templates


def calculate_stat_bonuses(
    character: "Character | NPC",
    equipped_templates: list["ItemTemplate"] | None = None,
) -> dict[str, float]:
    """
    Calculate stat bonuses from equipped items.

    Args:
        character: Character or NPC
        equipped_templates: Optional pre-loaded list of equipped item templates

    Returns:
        Dictionary mapping stat names to bonus values (e.g., {'STR': 5.0, 'DEX': 2.0})
    """
    bonuses: dict[str, float] = {}

    if equipped_templates is None:
        # If templates not provided, we can't calculate (need postgres_manager)
        return bonuses

    for template in equipped_templates:
        if template.stat_bonuses:
            for stat, bonus in template.stat_bonuses.items():
                bonuses[stat] = bonuses.get(stat, 0.0) + float(bonus)

    return bonuses


def calculate_stat_multipliers(
    character: "Character | NPC",
    equipped_templates: list["ItemTemplate"] | None = None,
) -> dict[str, float]:
    """
    Calculate stat multipliers from equipped items.

    Args:
        character: Character or NPC
        equipped_templates: Optional pre-loaded list of equipped item templates

    Returns:
        Dictionary mapping stat names to multiplier values (e.g., {'INT': 1.2})
    """
    multipliers: dict[str, float] = {}

    if equipped_templates is None:
        return multipliers

    for template in equipped_templates:
        if template.stat_multipliers:
            for stat, multiplier in template.stat_multipliers.items():
                current = multipliers.get(stat, 1.0)
                multipliers[stat] = current * float(multiplier)

    return multipliers


def calculate_resource_bonuses(
    character: "Character | NPC",
    equipped_templates: list["ItemTemplate"] | None = None,
) -> dict[str, float]:
    """
    Calculate max resource bonuses from equipped items.

    Args:
        character: Character or NPC
        equipped_templates: Optional pre-loaded list of equipped item templates

    Returns:
        Dictionary mapping resource names to bonus values (e.g., {'max_health': 20.0, 'max_stamina': 10.0})
    """
    bonuses: dict[str, float] = {}

    if equipped_templates is None:
        return bonuses

    for template in equipped_templates:
        if template.resource_bonuses:
            for resource, bonus in template.resource_bonuses.items():
                bonuses[resource] = bonuses.get(resource, 0.0) + float(bonus)

    return bonuses


def calculate_damage_bonuses(
    character: "Character | NPC",
    equipped_templates: list["ItemTemplate"] | None = None,
) -> dict[str, float]:
    """
    Calculate damage type bonuses from equipped items.

    Args:
        character: Character or NPC
        equipped_templates: Optional pre-loaded list of equipped item templates

    Returns:
        Dictionary mapping damage types to bonus values (e.g., {'physical': 10.0, 'tech': 5.0})
    """
    bonuses: dict[str, float] = {}

    if equipped_templates is None:
        return bonuses

    for template in equipped_templates:
        if template.damage_bonuses:
            for damage_type, bonus in template.damage_bonuses.items():
                bonuses[damage_type] = bonuses.get(damage_type, 0.0) + float(bonus)

    return bonuses


def calculate_damage_multipliers(
    character: "Character | NPC",
    equipped_templates: list["ItemTemplate"] | None = None,
) -> dict[str, float]:
    """
    Calculate damage type multipliers from equipped items.

    Args:
        character: Character or NPC
        equipped_templates: Optional pre-loaded list of equipped item templates

    Returns:
        Dictionary mapping damage types to multiplier values (e.g., {'physical': 1.15})
    """
    multipliers: dict[str, float] = {}

    if equipped_templates is None:
        return multipliers

    for template in equipped_templates:
        if template.damage_multipliers:
            for damage_type, multiplier in template.damage_multipliers.items():
                current = multipliers.get(damage_type, 1.0)
                multipliers[damage_type] = current * float(multiplier)

    return multipliers


def calculate_healing_bonuses(
    character: "Character | NPC",
    equipped_templates: list["ItemTemplate"] | None = None,
) -> dict[str, float]:
    """
    Calculate healing bonuses from equipped items.

    Args:
        character: Character or NPC
        equipped_templates: Optional pre-loaded list of equipped item templates

    Returns:
        Dictionary of healing bonuses (e.g., {'heal_amount': 5.0})
    """
    bonuses: dict[str, float] = {}

    if equipped_templates is None:
        return bonuses

    for template in equipped_templates:
        if template.healing_bonuses:
            for key, bonus in template.healing_bonuses.items():
                bonuses[key] = bonuses.get(key, 0.0) + float(bonus)

    return bonuses


def get_inventory_slots_bonus(
    character: "Character | NPC",
    equipped_templates: list["ItemTemplate"] | None = None,
) -> int:
    """
    Calculate additional inventory slots from equipped items.

    Args:
        character: Character or NPC
        equipped_templates: Optional pre-loaded list of equipped item templates

    Returns:
        Total additional inventory slots
    """
    if equipped_templates is None:
        return 0

    total_bonus = 0
    for template in equipped_templates:
        total_bonus += template.inventory_slots_bonus

    return total_bonus
