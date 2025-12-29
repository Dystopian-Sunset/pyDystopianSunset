"""Tests for equipment effect calculator functions."""

import pytest
from unittest.mock import MagicMock

from ds_common.equipment.effect_calculator import (
    calculate_stat_bonuses,
    calculate_stat_multipliers,
    calculate_resource_bonuses,
    calculate_damage_bonuses,
    calculate_damage_multipliers,
    calculate_healing_bonuses,
    get_inventory_slots_bonus,
)


class TestCalculateStatBonuses:
    """Tests for calculate_stat_bonuses function."""

    def test_returns_empty_dict_when_no_templates(self):
        """Test that empty dict is returned when no templates provided."""
        character = MagicMock()
        result = calculate_stat_bonuses(character, equipped_templates=None)
        assert result == {}

    def test_returns_empty_dict_for_empty_list(self):
        """Test that empty dict is returned for empty template list."""
        character = MagicMock()
        result = calculate_stat_bonuses(character, equipped_templates=[])
        assert result == {}

    def test_calculates_single_item_bonuses(self):
        """Test calculating bonuses from a single item."""
        character = MagicMock()

        item = MagicMock()
        item.stat_bonuses = {"STR": 5, "DEX": 3}

        result = calculate_stat_bonuses(character, equipped_templates=[item])

        assert result["STR"] == 5.0
        assert result["DEX"] == 3.0

    def test_aggregates_bonuses_from_multiple_items(self):
        """Test that bonuses from multiple items are summed."""
        character = MagicMock()

        item1 = MagicMock()
        item1.stat_bonuses = {"STR": 5, "DEX": 3}

        item2 = MagicMock()
        item2.stat_bonuses = {"STR": 2, "INT": 4}

        result = calculate_stat_bonuses(character, equipped_templates=[item1, item2])

        assert result["STR"] == 7.0  # 5 + 2
        assert result["DEX"] == 3.0
        assert result["INT"] == 4.0

    def test_handles_items_with_no_bonuses(self):
        """Test that items with None stat_bonuses are skipped."""
        character = MagicMock()

        item1 = MagicMock()
        item1.stat_bonuses = {"STR": 5}

        item2 = MagicMock()
        item2.stat_bonuses = None

        result = calculate_stat_bonuses(character, equipped_templates=[item1, item2])

        assert result["STR"] == 5.0

    def test_handles_float_bonuses(self):
        """Test that float bonuses are handled correctly."""
        character = MagicMock()

        item = MagicMock()
        item.stat_bonuses = {"STR": 2.5, "DEX": 1.3}

        result = calculate_stat_bonuses(character, equipped_templates=[item])

        assert result["STR"] == 2.5
        assert result["DEX"] == 1.3


class TestCalculateStatMultipliers:
    """Tests for calculate_stat_multipliers function."""

    def test_returns_empty_dict_when_no_templates(self):
        """Test that empty dict is returned when no templates provided."""
        character = MagicMock()
        result = calculate_stat_multipliers(character, equipped_templates=None)
        assert result == {}

    def test_calculates_single_item_multiplier(self):
        """Test calculating multipliers from a single item."""
        character = MagicMock()

        item = MagicMock()
        item.stat_multipliers = {"INT": 1.2, "CHA": 1.1}

        result = calculate_stat_multipliers(character, equipped_templates=[item])

        assert result["INT"] == 1.2
        assert result["CHA"] == 1.1

    def test_multiplies_multipliers_from_multiple_items(self):
        """Test that multipliers from multiple items are multiplied together."""
        character = MagicMock()

        item1 = MagicMock()
        item1.stat_multipliers = {"INT": 1.2}

        item2 = MagicMock()
        item2.stat_multipliers = {"INT": 1.5}

        result = calculate_stat_multipliers(character, equipped_templates=[item1, item2])

        # 1.0 * 1.2 * 1.5 = 1.8
        assert result["INT"] == pytest.approx(1.8)

    def test_handles_items_with_no_multipliers(self):
        """Test that items with None stat_multipliers are skipped."""
        character = MagicMock()

        item1 = MagicMock()
        item1.stat_multipliers = {"INT": 1.5}

        item2 = MagicMock()
        item2.stat_multipliers = None

        result = calculate_stat_multipliers(character, equipped_templates=[item1, item2])

        assert result["INT"] == 1.5


class TestCalculateResourceBonuses:
    """Tests for calculate_resource_bonuses function."""

    def test_returns_empty_dict_when_no_templates(self):
        """Test that empty dict is returned when no templates provided."""
        character = MagicMock()
        result = calculate_resource_bonuses(character, equipped_templates=None)
        assert result == {}

    def test_calculates_single_item_resource_bonuses(self):
        """Test calculating resource bonuses from a single item."""
        character = MagicMock()

        item = MagicMock()
        item.resource_bonuses = {"max_health": 20, "max_stamina": 10}

        result = calculate_resource_bonuses(character, equipped_templates=[item])

        assert result["max_health"] == 20.0
        assert result["max_stamina"] == 10.0

    def test_aggregates_resource_bonuses_from_multiple_items(self):
        """Test that resource bonuses from multiple items are summed."""
        character = MagicMock()

        item1 = MagicMock()
        item1.resource_bonuses = {"max_health": 20, "max_stamina": 10}

        item2 = MagicMock()
        item2.resource_bonuses = {"max_health": 15, "max_armor": 5}

        result = calculate_resource_bonuses(character, equipped_templates=[item1, item2])

        assert result["max_health"] == 35.0  # 20 + 15
        assert result["max_stamina"] == 10.0
        assert result["max_armor"] == 5.0

    def test_handles_items_with_no_resource_bonuses(self):
        """Test that items with None resource_bonuses are skipped."""
        character = MagicMock()

        item1 = MagicMock()
        item1.resource_bonuses = {"max_health": 20}

        item2 = MagicMock()
        item2.resource_bonuses = None

        result = calculate_resource_bonuses(character, equipped_templates=[item1, item2])

        assert result["max_health"] == 20.0


class TestCalculateDamageBonuses:
    """Tests for calculate_damage_bonuses function."""

    def test_returns_empty_dict_when_no_templates(self):
        """Test that empty dict is returned when no templates provided."""
        character = MagicMock()
        result = calculate_damage_bonuses(character, equipped_templates=None)
        assert result == {}

    def test_calculates_single_item_damage_bonuses(self):
        """Test calculating damage bonuses from a single item."""
        character = MagicMock()

        item = MagicMock()
        item.damage_bonuses = {"physical": 10, "tech": 5}

        result = calculate_damage_bonuses(character, equipped_templates=[item])

        assert result["physical"] == 10.0
        assert result["tech"] == 5.0

    def test_aggregates_damage_bonuses_from_multiple_items(self):
        """Test that damage bonuses from multiple items are summed."""
        character = MagicMock()

        item1 = MagicMock()
        item1.damage_bonuses = {"physical": 10, "tech": 5}

        item2 = MagicMock()
        item2.damage_bonuses = {"physical": 8, "fire": 3}

        result = calculate_damage_bonuses(character, equipped_templates=[item1, item2])

        assert result["physical"] == 18.0  # 10 + 8
        assert result["tech"] == 5.0
        assert result["fire"] == 3.0

    def test_handles_items_with_no_damage_bonuses(self):
        """Test that items with None damage_bonuses are skipped."""
        character = MagicMock()

        item1 = MagicMock()
        item1.damage_bonuses = {"physical": 10}

        item2 = MagicMock()
        item2.damage_bonuses = None

        result = calculate_damage_bonuses(character, equipped_templates=[item1, item2])

        assert result["physical"] == 10.0


class TestCalculateDamageMultipliers:
    """Tests for calculate_damage_multipliers function."""

    def test_returns_empty_dict_when_no_templates(self):
        """Test that empty dict is returned when no templates provided."""
        character = MagicMock()
        result = calculate_damage_multipliers(character, equipped_templates=None)
        assert result == {}

    def test_calculates_single_item_damage_multiplier(self):
        """Test calculating damage multipliers from a single item."""
        character = MagicMock()

        item = MagicMock()
        item.damage_multipliers = {"physical": 1.15, "tech": 1.1}

        result = calculate_damage_multipliers(character, equipped_templates=[item])

        assert result["physical"] == 1.15
        assert result["tech"] == 1.1

    def test_multiplies_damage_multipliers_from_multiple_items(self):
        """Test that damage multipliers from multiple items are multiplied together."""
        character = MagicMock()

        item1 = MagicMock()
        item1.damage_multipliers = {"physical": 1.2}

        item2 = MagicMock()
        item2.damage_multipliers = {"physical": 1.5}

        result = calculate_damage_multipliers(character, equipped_templates=[item1, item2])

        # 1.0 * 1.2 * 1.5 = 1.8
        assert result["physical"] == pytest.approx(1.8)

    def test_handles_items_with_no_damage_multipliers(self):
        """Test that items with None damage_multipliers are skipped."""
        character = MagicMock()

        item1 = MagicMock()
        item1.damage_multipliers = {"physical": 1.5}

        item2 = MagicMock()
        item2.damage_multipliers = None

        result = calculate_damage_multipliers(character, equipped_templates=[item1, item2])

        assert result["physical"] == 1.5


class TestCalculateHealingBonuses:
    """Tests for calculate_healing_bonuses function."""

    def test_returns_empty_dict_when_no_templates(self):
        """Test that empty dict is returned when no templates provided."""
        character = MagicMock()
        result = calculate_healing_bonuses(character, equipped_templates=None)
        assert result == {}

    def test_calculates_single_item_healing_bonuses(self):
        """Test calculating healing bonuses from a single item."""
        character = MagicMock()

        item = MagicMock()
        item.healing_bonuses = {"heal_amount": 5, "regen_rate": 2}

        result = calculate_healing_bonuses(character, equipped_templates=[item])

        assert result["heal_amount"] == 5.0
        assert result["regen_rate"] == 2.0

    def test_aggregates_healing_bonuses_from_multiple_items(self):
        """Test that healing bonuses from multiple items are summed."""
        character = MagicMock()

        item1 = MagicMock()
        item1.healing_bonuses = {"heal_amount": 5, "regen_rate": 2}

        item2 = MagicMock()
        item2.healing_bonuses = {"heal_amount": 3, "heal_over_time": 1}

        result = calculate_healing_bonuses(character, equipped_templates=[item1, item2])

        assert result["heal_amount"] == 8.0  # 5 + 3
        assert result["regen_rate"] == 2.0
        assert result["heal_over_time"] == 1.0

    def test_handles_items_with_no_healing_bonuses(self):
        """Test that items with None healing_bonuses are skipped."""
        character = MagicMock()

        item1 = MagicMock()
        item1.healing_bonuses = {"heal_amount": 5}

        item2 = MagicMock()
        item2.healing_bonuses = None

        result = calculate_healing_bonuses(character, equipped_templates=[item1, item2])

        assert result["heal_amount"] == 5.0


class TestGetInventorySlotsBonus:
    """Tests for get_inventory_slots_bonus function."""

    def test_returns_zero_when_no_templates(self):
        """Test that 0 is returned when no templates provided."""
        character = MagicMock()
        result = get_inventory_slots_bonus(character, equipped_templates=None)
        assert result == 0

    def test_returns_zero_for_empty_list(self):
        """Test that 0 is returned for empty template list."""
        character = MagicMock()
        result = get_inventory_slots_bonus(character, equipped_templates=[])
        assert result == 0

    def test_calculates_single_item_slots_bonus(self):
        """Test calculating inventory slots from a single item."""
        character = MagicMock()

        item = MagicMock()
        item.inventory_slots_bonus = 5

        result = get_inventory_slots_bonus(character, equipped_templates=[item])

        assert result == 5

    def test_sums_slots_from_multiple_items(self):
        """Test that inventory slots from multiple items are summed."""
        character = MagicMock()

        item1 = MagicMock()
        item1.inventory_slots_bonus = 5

        item2 = MagicMock()
        item2.inventory_slots_bonus = 3

        item3 = MagicMock()
        item3.inventory_slots_bonus = 2

        result = get_inventory_slots_bonus(character, equipped_templates=[item1, item2, item3])

        assert result == 10  # 5 + 3 + 2

    def test_handles_zero_slot_bonuses(self):
        """Test that items with 0 slot bonuses don't affect result."""
        character = MagicMock()

        item1 = MagicMock()
        item1.inventory_slots_bonus = 5

        item2 = MagicMock()
        item2.inventory_slots_bonus = 0

        result = get_inventory_slots_bonus(character, equipped_templates=[item1, item2])

        assert result == 5

    def test_handles_negative_slot_bonuses(self):
        """Test that negative slot bonuses are summed correctly."""
        character = MagicMock()

        item1 = MagicMock()
        item1.inventory_slots_bonus = 5

        item2 = MagicMock()
        item2.inventory_slots_bonus = -2

        result = get_inventory_slots_bonus(character, equipped_templates=[item1, item2])

        assert result == 3  # 5 + (-2)
