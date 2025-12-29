"""
Display formatting utilities for combat resources.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ds_common.models.character import Character
    from ds_common.models.npc import NPC


def format_resource_display(character: "Character | NPC") -> dict[str, int]:
    """
    Format float resources as integers for display to players.

    Args:
        character: Character or NPC to format

    Returns:
        Dictionary with integer-formatted resource values
    """
    return {
        "current_health": int(character.current_health),
        "max_health": int(character.max_health),
        "current_stamina": int(character.current_stamina),
        "max_stamina": int(character.max_stamina),
        "current_tech_power": int(character.current_tech_power),
        "max_tech_power": int(character.max_tech_power),
        "current_armor": int(character.current_armor),
        "max_armor": int(character.max_armor),
        "is_incapacitated": character.is_incapacitated,
    }


def format_combat_status(character: "Character | NPC") -> str:
    """
    Format combat status for player viewing.

    Args:
        character: Character or NPC to format

    Returns:
        Formatted string with combat status
    """
    resources = format_resource_display(character)

    status_parts = [
        f"Health: {resources['current_health']}/{resources['max_health']}",
        f"Stamina: {resources['current_stamina']}/{resources['max_stamina']}",
        f"Tech Power: {resources['current_tech_power']}/{resources['max_tech_power']}",
        f"Armor: {resources['current_armor']}/{resources['max_armor']}",
    ]

    if resources["is_incapacitated"]:
        status_parts.append("Status: INCAPACITATED")

    return " | ".join(status_parts)
