"""
Equipment validation service for checking slot/item compatibility.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ds_common.models.character import Character
    from ds_common.models.item_template import ItemTemplate


def validate_item_slot_compatibility(
    item_template: "ItemTemplate",
    slot: str,
) -> bool:
    """
    Validate that an item can be equipped to a specific slot.

    Args:
        item_template: Item template to check
        slot: Equipment slot name

    Returns:
        True if item can be equipped to slot, False otherwise
    """
    if not item_template.equippable_slots:
        return False

    return slot in item_template.equippable_slots


def validate_equipment_requirements(
    character: "Character",
    item_template: "ItemTemplate",
) -> tuple[bool, str | None]:
    """
    Validate that a character meets the requirements to equip an item.

    Args:
        character: Character attempting to equip
        item_template: Item template to check

    Returns:
        Tuple of (is_valid, error_message)
        If is_valid is True, error_message is None
        If is_valid is False, error_message contains the reason
    """
    # Future enhancement: Add level requirements, stat requirements, etc.
    # For now, all items are equippable if they fit the slot
    return (True, None)
