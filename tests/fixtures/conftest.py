"""Shared pytest fixtures for all tests."""

import pytest
from unittest.mock import MagicMock
from uuid import uuid4


@pytest.fixture
def mock_character():
    """Create a mock character for testing."""
    character = MagicMock()
    character.id = uuid4()
    character.name = "Test Character"
    character.level = 1
    character.exp = 0
    character.stats = {
        "STR": 10,
        "DEX": 10,
        "INT": 10,
        "PER": 10,
        "CHA": 10,
        "LUK": 10,
    }
    character.max_health = 100
    character.current_health = 100
    character.max_armor = 50
    character.current_armor = 50
    return character


@pytest.fixture
def mock_item_template():
    """Create a mock item template for testing."""
    item = MagicMock()
    item.id = uuid4()
    item.name = "Test Weapon"
    item.item_type = "weapon"
    item.equippable_slots = ["main_hand", "off_hand"]
    item.stat_modifiers = {"STR": 2, "DEX": 1}
    return item


@pytest.fixture
def mock_non_equippable_item():
    """Create a mock non-equippable item for testing."""
    item = MagicMock()
    item.id = uuid4()
    item.name = "Test Consumable"
    item.item_type = "consumable"
    item.equippable_slots = None
    item.stat_modifiers = {}
    return item
