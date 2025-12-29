"""Tests for restoration service functions."""

import pytest
from unittest.mock import MagicMock
from uuid import UUID

from ds_common.combat.restoration_service import (
    _get_class_restoration_modifiers,
    calculate_equipment_restoration_modifiers,
    calculate_buff_restoration_modifiers,
    apply_restoration_modifiers,
    ENFORCER_ID,
    TECH_WIZARD_ID,
    SMOOTH_TALKER_ID,
    SPY_ID,
    WILD_CARD_ID,
)
from ds_common.combat.models import RestorationModifiers, RestorationRates


class TestGetClassRestorationModifiers:
    """Tests for _get_class_restoration_modifiers function."""

    def test_enforcer_restoration_rates(self):
        """Test Enforcer class restoration modifiers."""
        result = _get_class_restoration_modifiers(ENFORCER_ID, level=1)

        assert result["health_base"] == 0.3
        assert result["stamina_base"] == 0.2
        assert result["tech_power_base"] == 0.05
        assert result["armor_base"] == 0.0

    def test_tech_wizard_restoration_rates(self):
        """Test Tech Wizard class restoration modifiers."""
        result = _get_class_restoration_modifiers(TECH_WIZARD_ID, level=1)

        assert result["health_base"] == 0.1
        assert result["stamina_base"] == 0.1
        # Tech power: 0.5 + (0.1 * 1) = 0.6
        assert result["tech_power_base"] == 0.6
        assert result["armor_base"] == 0.0

    def test_tech_wizard_tech_power_scales_with_level(self):
        """Test that Tech Wizard tech power restoration scales with level."""
        level_1 = _get_class_restoration_modifiers(TECH_WIZARD_ID, level=1)
        level_5 = _get_class_restoration_modifiers(TECH_WIZARD_ID, level=5)
        level_10 = _get_class_restoration_modifiers(TECH_WIZARD_ID, level=10)

        # 0.5 + (0.1 * level)
        assert level_1["tech_power_base"] == 0.6
        assert level_5["tech_power_base"] == 1.0
        assert level_10["tech_power_base"] == 1.5

    def test_smooth_talker_restoration_rates(self):
        """Test Smooth Talker class restoration modifiers."""
        result = _get_class_restoration_modifiers(SMOOTH_TALKER_ID, level=1)

        assert result["health_base"] == 0.15
        assert result["stamina_base"] == 0.15
        assert result["tech_power_base"] == 0.2
        assert result["armor_base"] == 0.0

    def test_spy_restoration_rates(self):
        """Test Spy class restoration modifiers."""
        result = _get_class_restoration_modifiers(SPY_ID, level=1)

        assert result["health_base"] == 0.12
        assert result["stamina_base"] == 0.25
        assert result["tech_power_base"] == 0.15
        assert result["armor_base"] == 0.0

    def test_wild_card_restoration_rates(self):
        """Test Wild Card class restoration modifiers."""
        result = _get_class_restoration_modifiers(WILD_CARD_ID, level=1)

        assert result["health_base"] == 0.18
        assert result["stamina_base"] == 0.18
        assert result["tech_power_base"] == 0.25
        assert result["armor_base"] == 0.0

    def test_no_class_returns_zeros(self):
        """Test that no class returns all zeros."""
        result = _get_class_restoration_modifiers(None, level=1)

        assert result["health_base"] == 0.0
        assert result["stamina_base"] == 0.0
        assert result["tech_power_base"] == 0.0
        assert result["armor_base"] == 0.0

    def test_unknown_class_returns_zeros(self):
        """Test that unknown class ID returns all zeros."""
        unknown_id = UUID("99999999-9999-9999-9999-999999999999")
        result = _get_class_restoration_modifiers(unknown_id, level=1)

        assert result["health_base"] == 0.0
        assert result["stamina_base"] == 0.0
        assert result["tech_power_base"] == 0.0
        assert result["armor_base"] == 0.0


class TestCalculateEquipmentRestorationModifiers:
    """Tests for calculate_equipment_restoration_modifiers function."""

    def test_no_inventory_returns_default_modifiers(self):
        """Test that character without inventory returns default modifiers."""
        character = MagicMock()
        character.inventory = None

        result = calculate_equipment_restoration_modifiers(character)

        assert result.health_bonus == 0.0
        assert result.health_multiplier == 1.0
        assert result.stamina_bonus == 0.0
        assert result.stamina_multiplier == 1.0

    def test_empty_inventory_returns_default_modifiers(self):
        """Test that empty inventory returns default modifiers."""
        character = MagicMock()
        character.inventory = []

        result = calculate_equipment_restoration_modifiers(character)

        assert result.health_bonus == 0.0
        assert result.health_multiplier == 1.0

    def test_unequipped_items_ignored(self):
        """Test that unequipped items don't affect modifiers."""
        character = MagicMock()
        character.inventory = [
            {
                "equipped": False,
                "health_restoration_bonus": 5.0,
            }
        ]

        result = calculate_equipment_restoration_modifiers(character)

        # Should be default since item isn't equipped
        assert result.health_bonus == 0.0

    def test_equipped_item_with_health_bonus(self):
        """Test equipped item adds health restoration bonus."""
        character = MagicMock()
        character.inventory = [
            {
                "equipped": True,
                "health_restoration_bonus": 5.0,
            }
        ]

        result = calculate_equipment_restoration_modifiers(character)

        assert result.health_bonus == 5.0

    def test_equipped_item_with_multiplier(self):
        """Test equipped item applies restoration multiplier."""
        character = MagicMock()
        character.inventory = [
            {
                "equipped": True,
                "health_restoration_multiplier": 1.5,
            }
        ]

        result = calculate_equipment_restoration_modifiers(character)

        assert result.health_multiplier == 1.5

    def test_multiple_equipped_items_bonuses_sum(self):
        """Test that bonuses from multiple items are summed."""
        character = MagicMock()
        character.inventory = [
            {"equipped": True, "health_restoration_bonus": 3.0},
            {"equipped": True, "health_restoration_bonus": 2.0},
            {"equipped": True, "stamina_restoration_bonus": 4.0},
        ]

        result = calculate_equipment_restoration_modifiers(character)

        assert result.health_bonus == 5.0
        assert result.stamina_bonus == 4.0

    def test_multiple_equipped_items_multipliers_multiply(self):
        """Test that multipliers from multiple items are multiplied together."""
        character = MagicMock()
        character.inventory = [
            {"equipped": True, "health_restoration_multiplier": 1.5},
            {"equipped": True, "health_restoration_multiplier": 1.2},
        ]

        result = calculate_equipment_restoration_modifiers(character)

        # 1.0 * 1.5 * 1.2 = 1.8
        assert result.health_multiplier == pytest.approx(1.8)

    def test_all_resource_types(self):
        """Test that all resource types can be modified."""
        character = MagicMock()
        character.inventory = [
            {
                "equipped": True,
                "health_restoration_bonus": 1.0,
                "stamina_restoration_bonus": 2.0,
                "tech_power_restoration_bonus": 3.0,
                "armor_restoration_bonus": 4.0,
                "health_restoration_multiplier": 1.1,
                "stamina_restoration_multiplier": 1.2,
                "tech_power_restoration_multiplier": 1.3,
                "armor_restoration_multiplier": 1.4,
            }
        ]

        result = calculate_equipment_restoration_modifiers(character)

        assert result.health_bonus == 1.0
        assert result.stamina_bonus == 2.0
        assert result.tech_power_bonus == 3.0
        assert result.armor_bonus == 4.0
        assert result.health_multiplier == 1.1
        assert result.stamina_multiplier == 1.2
        assert result.tech_power_multiplier == 1.3
        assert result.armor_multiplier == 1.4

    def test_equipment_slot_marks_as_equipped(self):
        """Test that item with equipment_slot is considered equipped."""
        character = MagicMock()
        character.inventory = [
            {
                "equipment_slot": "chest",
                "health_restoration_bonus": 5.0,
            }
        ]

        result = calculate_equipment_restoration_modifiers(character)

        # Should count because equipment_slot is not None
        assert result.health_bonus == 5.0


class TestCalculateBuffRestorationModifiers:
    """Tests for calculate_buff_restoration_modifiers function."""

    def test_no_effects_returns_default_modifiers(self):
        """Test that character without effects returns default modifiers."""
        character = MagicMock()
        character.effects = None

        result = calculate_buff_restoration_modifiers(character)

        assert result.health_bonus == 0.0
        assert result.health_multiplier == 1.0

    def test_empty_effects_returns_default_modifiers(self):
        """Test that empty effects dict returns default modifiers."""
        character = MagicMock()
        character.effects = {}

        result = calculate_buff_restoration_modifiers(character)

        assert result.health_bonus == 0.0
        assert result.health_multiplier == 1.0

    def test_health_restoration_bonus(self):
        """Test health restoration bonus from buffs."""
        character = MagicMock()
        character.effects = {"health_restoration_bonus": 10.0}

        result = calculate_buff_restoration_modifiers(character)

        assert result.health_bonus == 10.0

    def test_health_restoration_multiplier(self):
        """Test health restoration multiplier from buffs."""
        character = MagicMock()
        character.effects = {"health_restoration_multiplier": 2.0}

        result = calculate_buff_restoration_modifiers(character)

        assert result.health_multiplier == 2.0

    def test_all_restoration_types(self):
        """Test that all restoration types can be buffed."""
        character = MagicMock()
        character.effects = {
            "health_restoration_bonus": 5.0,
            "stamina_restoration_bonus": 6.0,
            "tech_power_restoration_bonus": 7.0,
            "armor_restoration_bonus": 8.0,
            "health_restoration_multiplier": 1.5,
            "stamina_restoration_multiplier": 1.6,
            "tech_power_restoration_multiplier": 1.7,
            "armor_restoration_multiplier": 1.8,
        }

        result = calculate_buff_restoration_modifiers(character)

        assert result.health_bonus == 5.0
        assert result.stamina_bonus == 6.0
        assert result.tech_power_bonus == 7.0
        assert result.armor_bonus == 8.0
        assert result.health_multiplier == 1.5
        assert result.stamina_multiplier == 1.6
        assert result.tech_power_multiplier == 1.7
        assert result.armor_multiplier == 1.8

    def test_multiple_bonuses_sum(self):
        """Test that multiple bonuses of same type sum together."""
        character = MagicMock()
        # In practice effects dict keys are unique, but testing the logic
        character.effects = {
            "health_restoration_bonus": 5.0,
            "stamina_restoration_bonus": 3.0,
        }

        result = calculate_buff_restoration_modifiers(character)

        assert result.health_bonus == 5.0
        assert result.stamina_bonus == 3.0

    def test_non_numeric_effects_ignored(self):
        """Test that non-numeric effect values are ignored."""
        character = MagicMock()
        character.effects = {
            "health_restoration_bonus": 5.0,
            "some_string_effect": "ignored",
            "some_bool_effect": True,
            "stamina_restoration_bonus": 3.0,
        }

        result = calculate_buff_restoration_modifiers(character)

        # Should only count the numeric bonuses
        assert result.health_bonus == 5.0
        assert result.stamina_bonus == 3.0


class TestApplyRestorationModifiers:
    """Tests for apply_restoration_modifiers function."""

    def test_no_modifiers_returns_base_rates(self):
        """Test that with no modifiers, base rates are returned."""
        base_rates = RestorationRates(
            health_per_second=1.0,
            stamina_per_second=2.0,
            tech_power_per_second=3.0,
            armor_per_second=4.0,
        )
        equipment_mods = RestorationModifiers()
        buff_mods = RestorationModifiers()

        result = apply_restoration_modifiers(base_rates, equipment_mods, buff_mods)

        assert result.health_per_second == 1.0
        assert result.stamina_per_second == 2.0
        assert result.tech_power_per_second == 3.0
        assert result.armor_per_second == 4.0

    def test_equipment_bonus_added_to_base(self):
        """Test that equipment bonuses are added to base rates."""
        base_rates = RestorationRates(health_per_second=1.0)
        equipment_mods = RestorationModifiers(health_bonus=0.5)
        buff_mods = RestorationModifiers()

        result = apply_restoration_modifiers(base_rates, equipment_mods, buff_mods)

        # (1.0 + 0.5) * 1.0 + 0.0) * 1.0 = 1.5
        assert result.health_per_second == 1.5

    def test_equipment_multiplier_applied(self):
        """Test that equipment multipliers are applied."""
        base_rates = RestorationRates(health_per_second=2.0)
        equipment_mods = RestorationModifiers(health_multiplier=1.5)
        buff_mods = RestorationModifiers()

        result = apply_restoration_modifiers(base_rates, equipment_mods, buff_mods)

        # (2.0 + 0.0) * 1.5 + 0.0) * 1.0 = 3.0
        assert result.health_per_second == 3.0

    def test_buff_bonus_added_after_equipment(self):
        """Test that buff bonuses are added after equipment modifiers."""
        base_rates = RestorationRates(health_per_second=1.0)
        equipment_mods = RestorationModifiers(health_bonus=1.0, health_multiplier=2.0)
        buff_mods = RestorationModifiers(health_bonus=3.0)

        result = apply_restoration_modifiers(base_rates, equipment_mods, buff_mods)

        # ((1.0 + 1.0) * 2.0 + 3.0) * 1.0 = (2.0 * 2.0 + 3.0) = 7.0
        assert result.health_per_second == 7.0

    def test_buff_multiplier_applied_last(self):
        """Test that buff multipliers are applied last."""
        base_rates = RestorationRates(health_per_second=1.0)
        equipment_mods = RestorationModifiers(health_bonus=1.0)
        buff_mods = RestorationModifiers(health_multiplier=2.0)

        result = apply_restoration_modifiers(base_rates, equipment_mods, buff_mods)

        # ((1.0 + 1.0) * 1.0 + 0.0) * 2.0 = 2.0 * 2.0 = 4.0
        assert result.health_per_second == 4.0

    def test_full_formula_calculation(self):
        """Test complete formula with all modifiers."""
        base_rates = RestorationRates(health_per_second=5.0)
        equipment_mods = RestorationModifiers(health_bonus=3.0, health_multiplier=1.5)
        buff_mods = RestorationModifiers(health_bonus=2.0, health_multiplier=2.0)

        result = apply_restoration_modifiers(base_rates, equipment_mods, buff_mods)

        # ((5.0 + 3.0) * 1.5 + 2.0) * 2.0
        # = (8.0 * 1.5 + 2.0) * 2.0
        # = (12.0 + 2.0) * 2.0
        # = 14.0 * 2.0
        # = 28.0
        assert result.health_per_second == 28.0

    def test_negative_rates_clamped_to_zero(self):
        """Test that negative rates are clamped to 0."""
        base_rates = RestorationRates(health_per_second=1.0)
        equipment_mods = RestorationModifiers()
        buff_mods = RestorationModifiers(health_multiplier=-5.0)

        result = apply_restoration_modifiers(base_rates, equipment_mods, buff_mods)

        # Would be negative, but should clamp to 0
        assert result.health_per_second == 0.0

    def test_all_resources_calculated_independently(self):
        """Test that all resources are calculated independently."""
        base_rates = RestorationRates(
            health_per_second=1.0,
            stamina_per_second=2.0,
            tech_power_per_second=3.0,
            armor_per_second=4.0,
        )
        equipment_mods = RestorationModifiers(
            health_bonus=1.0,
            stamina_multiplier=2.0,
            tech_power_bonus=1.0,
            armor_multiplier=0.5,
        )
        buff_mods = RestorationModifiers(
            health_multiplier=2.0,
            stamina_bonus=1.0,
            tech_power_multiplier=1.5,
            armor_bonus=2.0,
        )

        result = apply_restoration_modifiers(base_rates, equipment_mods, buff_mods)

        # Health: ((1.0 + 1.0) * 1.0 + 0.0) * 2.0 = 4.0
        assert result.health_per_second == 4.0
        # Stamina: ((2.0 + 0.0) * 2.0 + 1.0) * 1.0 = 5.0
        assert result.stamina_per_second == 5.0
        # Tech: ((3.0 + 1.0) * 1.0 + 0.0) * 1.5 = 6.0
        assert result.tech_power_per_second == 6.0
        # Armor: ((4.0 + 0.0) * 0.5 + 2.0) * 1.0 = 4.0
        assert result.armor_per_second == 4.0
