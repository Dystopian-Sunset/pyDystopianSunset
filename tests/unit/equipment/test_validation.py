"""Tests for equipment validation service."""

import pytest
from unittest.mock import MagicMock

from ds_common.equipment.validation import (
    validate_item_slot_compatibility,
    validate_equipment_requirements,
)


class TestValidateItemSlotCompatibility:
    """Tests for validate_item_slot_compatibility function."""

    def test_item_can_be_equipped_to_valid_slot(self):
        """Test that item can be equipped to a slot it's compatible with."""
        item = MagicMock()
        item.equippable_slots = ["main_hand", "off_hand"]

        result = validate_item_slot_compatibility(item, "main_hand")

        assert result is True

    def test_item_can_be_equipped_to_any_valid_slot(self):
        """Test that item can be equipped to any of its valid slots."""
        item = MagicMock()
        item.equippable_slots = ["head", "chest", "legs"]

        assert validate_item_slot_compatibility(item, "head") is True
        assert validate_item_slot_compatibility(item, "chest") is True
        assert validate_item_slot_compatibility(item, "legs") is True

    def test_item_cannot_be_equipped_to_invalid_slot(self):
        """Test that item cannot be equipped to incompatible slot."""
        item = MagicMock()
        item.equippable_slots = ["main_hand"]

        result = validate_item_slot_compatibility(item, "head")

        assert result is False

    def test_non_equippable_item_returns_false(self):
        """Test that non-equippable items (no slots) return False."""
        item = MagicMock()
        item.equippable_slots = None

        result = validate_item_slot_compatibility(item, "main_hand")

        assert result is False

    def test_item_with_empty_slots_list_returns_false(self):
        """Test that items with empty equippable_slots list return False."""
        item = MagicMock()
        item.equippable_slots = []

        result = validate_item_slot_compatibility(item, "main_hand")

        assert result is False

    def test_case_sensitive_slot_matching(self):
        """Test that slot matching is case-sensitive."""
        item = MagicMock()
        item.equippable_slots = ["main_hand"]

        # Should be case-sensitive (main_hand != Main_Hand)
        assert validate_item_slot_compatibility(item, "main_hand") is True
        assert validate_item_slot_compatibility(item, "Main_Hand") is False

    def test_two_handed_weapon_example(self):
        """Test realistic scenario: two-handed weapon can go in both hands."""
        two_handed_weapon = MagicMock()
        two_handed_weapon.equippable_slots = ["main_hand", "off_hand"]

        assert validate_item_slot_compatibility(two_handed_weapon, "main_hand") is True
        assert validate_item_slot_compatibility(two_handed_weapon, "off_hand") is True
        assert validate_item_slot_compatibility(two_handed_weapon, "head") is False

    def test_armor_piece_example(self):
        """Test realistic scenario: armor piece can only go in specific slot."""
        helmet = MagicMock()
        helmet.equippable_slots = ["head"]

        assert validate_item_slot_compatibility(helmet, "head") is True
        assert validate_item_slot_compatibility(helmet, "chest") is False
        assert validate_item_slot_compatibility(helmet, "main_hand") is False


class TestValidateEquipmentRequirements:
    """Tests for validate_equipment_requirements function."""

    def test_always_returns_true_currently(self):
        """Test that function currently always returns True (no requirements implemented)."""
        character = MagicMock()
        item = MagicMock()

        is_valid, error_message = validate_equipment_requirements(character, item)

        assert is_valid is True
        assert error_message is None

    def test_returns_tuple(self):
        """Test that function returns a tuple of (bool, str|None)."""
        character = MagicMock()
        item = MagicMock()

        result = validate_equipment_requirements(character, item)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert result[1] is None or isinstance(result[1], str)

    def test_low_level_character_can_equip_high_level_item(self):
        """Test that low level characters can equip any item (no level req yet)."""
        character = MagicMock()
        character.level = 1

        item = MagicMock()
        item.level_requirement = 10  # Even if item has level req, not checked yet

        is_valid, error_message = validate_equipment_requirements(character, item)

        # Should pass since requirements not implemented
        assert is_valid is True
        assert error_message is None

    def test_insufficient_stats_character_can_equip_item(self):
        """Test that characters with insufficient stats can equip items (no stat req yet)."""
        character = MagicMock()
        character.stats = {"STR": 5, "DEX": 5}

        item = MagicMock()
        item.stat_requirements = {"STR": 20, "DEX": 15}  # High requirements

        is_valid, error_message = validate_equipment_requirements(character, item)

        # Should pass since requirements not implemented
        assert is_valid is True
        assert error_message is None

    def test_with_various_character_levels(self):
        """Test that validation works for characters at any level."""
        item = MagicMock()

        for level in [1, 5, 10, 50, 100]:
            character = MagicMock()
            character.level = level

            is_valid, error_message = validate_equipment_requirements(character, item)

            assert is_valid is True
            assert error_message is None
