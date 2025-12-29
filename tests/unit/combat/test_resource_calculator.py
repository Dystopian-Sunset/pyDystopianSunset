"""Tests for combat resource calculator functions."""

import pytest
from unittest.mock import MagicMock
from uuid import UUID

from ds_common.combat.resource_calculator import (
    calculate_max_health,
    calculate_max_stamina,
    calculate_max_tech_power,
    calculate_max_armor,
    ENFORCER_ID,
    TECH_WIZARD_ID,
    SMOOTH_TALKER_ID,
    SPY_ID,
    WILD_CARD_ID,
)


class TestCalculateMaxHealth:
    """Tests for calculate_max_health function.

    Formula: (STR * 8) + (DEX * 2) + (level * 10) + class_modifier + equipment_bonus
    """

    def test_basic_health_calculation_no_class(self):
        """Test basic health calculation without class or equipment."""
        character = MagicMock()
        character.stats = {"STR": 10, "DEX": 10}
        character.level = 1
        character.character_class_id = None

        # (10 * 8) + (10 * 2) + (1 * 10) = 80 + 20 + 10 = 110
        result = calculate_max_health(character)

        assert result == 110.0

    def test_health_scales_with_strength(self):
        """Test that health scales properly with STR stat."""
        character = MagicMock()
        character.stats = {"STR": 20, "DEX": 10}
        character.level = 1
        character.character_class_id = None

        # (20 * 8) + (10 * 2) + (1 * 10) = 160 + 20 + 10 = 190
        result = calculate_max_health(character)

        assert result == 190.0

    def test_health_scales_with_dexterity(self):
        """Test that health scales with DEX stat (less than STR)."""
        character = MagicMock()
        character.stats = {"STR": 10, "DEX": 20}
        character.level = 1
        character.character_class_id = None

        # (10 * 8) + (20 * 2) + (1 * 10) = 80 + 40 + 10 = 130
        result = calculate_max_health(character)

        assert result == 130.0

    def test_health_scales_with_level(self):
        """Test that health increases with character level."""
        character = MagicMock()
        character.stats = {"STR": 10, "DEX": 10}
        character.level = 5
        character.character_class_id = None

        # (10 * 8) + (10 * 2) + (5 * 10) = 80 + 20 + 50 = 150
        result = calculate_max_health(character)

        assert result == 150.0

    def test_enforcer_class_health_bonus(self):
        """Test that Enforcer class gets health bonuses."""
        character = MagicMock()
        character.stats = {"STR": 10, "DEX": 10}
        character.level = 1
        character.character_class_id = ENFORCER_ID

        # Base: (10 * 8) + (10 * 2) + (1 * 10) = 110
        # Class: 50 + (5 * 1) = 55
        # Total: 165
        result = calculate_max_health(character)

        assert result == 165.0

    def test_enforcer_health_scales_with_level(self):
        """Test that Enforcer health bonus scales with level."""
        character = MagicMock()
        character.stats = {"STR": 10, "DEX": 10}
        character.level = 5
        character.character_class_id = ENFORCER_ID

        # Base: (10 * 8) + (10 * 2) + (5 * 10) = 150
        # Class: 50 + (5 * 5) = 75
        # Total: 225
        result = calculate_max_health(character)

        assert result == 225.0

    def test_tech_wizard_class_health(self):
        """Test Tech Wizard class health (lower base, no scaling)."""
        character = MagicMock()
        character.stats = {"STR": 10, "DEX": 10}
        character.level = 5
        character.character_class_id = TECH_WIZARD_ID

        # Base: (10 * 8) + (10 * 2) + (5 * 10) = 150
        # Class: 20 + (0 * 5) = 20
        # Total: 170
        result = calculate_max_health(character)

        assert result == 170.0

    def test_health_with_equipment_bonus(self):
        """Test that equipment bonuses are added to health."""
        character = MagicMock()
        character.stats = {"STR": 10, "DEX": 10}
        character.level = 1
        character.character_class_id = None

        equipment_bonuses = {"max_health": 25.0}

        # Base: 110 + Equipment: 25 = 135
        result = calculate_max_health(character, equipment_resource_bonuses=equipment_bonuses)

        assert result == 135.0

    def test_handles_missing_stats(self):
        """Test that missing stats default to 0."""
        character = MagicMock()
        character.stats = {}  # No stats
        character.level = 1
        character.character_class_id = None

        # (0 * 8) + (0 * 2) + (1 * 10) = 10
        result = calculate_max_health(character)

        assert result == 10.0


class TestCalculateMaxStamina:
    """Tests for calculate_max_stamina function.

    Formula: (DEX * 5) + (STR * 2) + (level * 5) + class_modifier + equipment_bonus
    """

    def test_basic_stamina_calculation_no_class(self):
        """Test basic stamina calculation without class or equipment."""
        character = MagicMock()
        character.stats = {"STR": 10, "DEX": 10}
        character.level = 1
        character.character_class_id = None

        # (10 * 5) + (10 * 2) + (1 * 5) = 50 + 20 + 5 = 75
        result = calculate_max_stamina(character)

        assert result == 75.0

    def test_stamina_scales_with_dexterity(self):
        """Test that stamina scales primarily with DEX."""
        character = MagicMock()
        character.stats = {"STR": 10, "DEX": 20}
        character.level = 1
        character.character_class_id = None

        # (20 * 5) + (10 * 2) + (1 * 5) = 100 + 20 + 5 = 125
        result = calculate_max_stamina(character)

        assert result == 125.0

    def test_stamina_scales_with_strength(self):
        """Test that stamina also scales with STR (less than DEX)."""
        character = MagicMock()
        character.stats = {"STR": 20, "DEX": 10}
        character.level = 1
        character.character_class_id = None

        # (10 * 5) + (20 * 2) + (1 * 5) = 50 + 40 + 5 = 95
        result = calculate_max_stamina(character)

        assert result == 95.0

    def test_stamina_scales_with_level(self):
        """Test that stamina increases with level."""
        character = MagicMock()
        character.stats = {"STR": 10, "DEX": 10}
        character.level = 5
        character.character_class_id = None

        # (10 * 5) + (10 * 2) + (5 * 5) = 50 + 20 + 25 = 95
        result = calculate_max_stamina(character)

        assert result == 95.0

    def test_spy_class_stamina_bonus(self):
        """Test that Spy class gets highest stamina bonus."""
        character = MagicMock()
        character.stats = {"STR": 10, "DEX": 10}
        character.level = 1
        character.character_class_id = SPY_ID

        # Base: (10 * 5) + (10 * 2) + (1 * 5) = 75
        # Class: 40 + (0 * 1) = 40
        # Total: 115
        result = calculate_max_stamina(character)

        assert result == 115.0

    def test_stamina_with_equipment_bonus(self):
        """Test that equipment bonuses are added to stamina."""
        character = MagicMock()
        character.stats = {"STR": 10, "DEX": 10}
        character.level = 1
        character.character_class_id = None

        equipment_bonuses = {"max_stamina": 20.0}

        # Base: 75 + Equipment: 20 = 95
        result = calculate_max_stamina(character, equipment_resource_bonuses=equipment_bonuses)

        assert result == 95.0


class TestCalculateMaxTechPower:
    """Tests for calculate_max_tech_power function.

    Formula: (INT * 10) + (level * 8) + class_modifier + equipment_bonus
    """

    def test_basic_tech_power_calculation_no_class(self):
        """Test basic tech power calculation without class or equipment."""
        character = MagicMock()
        character.stats = {"INT": 10}
        character.level = 1
        character.character_class_id = None

        # (10 * 10) + (1 * 8) = 100 + 8 = 108
        result = calculate_max_tech_power(character)

        assert result == 108.0

    def test_tech_power_scales_with_intelligence(self):
        """Test that tech power scales strongly with INT."""
        character = MagicMock()
        character.stats = {"INT": 20}
        character.level = 1
        character.character_class_id = None

        # (20 * 10) + (1 * 8) = 200 + 8 = 208
        result = calculate_max_tech_power(character)

        assert result == 208.0

    def test_tech_power_scales_with_level(self):
        """Test that tech power increases with level."""
        character = MagicMock()
        character.stats = {"INT": 10}
        character.level = 5
        character.character_class_id = None

        # (10 * 10) + (5 * 8) = 100 + 40 = 140
        result = calculate_max_tech_power(character)

        assert result == 140.0

    def test_tech_wizard_class_tech_power_bonus(self):
        """Test that Tech Wizard gets highest tech power bonuses."""
        character = MagicMock()
        character.stats = {"INT": 10}
        character.level = 1
        character.character_class_id = TECH_WIZARD_ID

        # Base: (10 * 10) + (1 * 8) = 108
        # Class: 50 + (10 * 1) = 60
        # Total: 168
        result = calculate_max_tech_power(character)

        assert result == 168.0

    def test_tech_wizard_tech_power_scales_with_level(self):
        """Test that Tech Wizard tech power scales well with level."""
        character = MagicMock()
        character.stats = {"INT": 10}
        character.level = 5
        character.character_class_id = TECH_WIZARD_ID

        # Base: (10 * 10) + (5 * 8) = 140
        # Class: 50 + (10 * 5) = 100
        # Total: 240
        result = calculate_max_tech_power(character)

        assert result == 240.0

    def test_tech_power_with_equipment_bonus(self):
        """Test that equipment bonuses are added to tech power."""
        character = MagicMock()
        character.stats = {"INT": 10}
        character.level = 1
        character.character_class_id = None

        equipment_bonuses = {"max_tech_power": 30.0}

        # Base: 108 + Equipment: 30 = 138
        result = calculate_max_tech_power(character, equipment_resource_bonuses=equipment_bonuses)

        assert result == 138.0

    def test_handles_missing_int_stat(self):
        """Test that missing INT stat defaults to 0."""
        character = MagicMock()
        character.stats = {}
        character.level = 1
        character.character_class_id = None

        # (0 * 10) + (1 * 8) = 8
        result = calculate_max_tech_power(character)

        assert result == 8.0


class TestCalculateMaxArmor:
    """Tests for calculate_max_armor function.

    Formula: (DEX * 3) + (level * 2) + equipment_bonus
    """

    def test_basic_armor_calculation(self):
        """Test basic armor calculation without equipment."""
        character = MagicMock()
        character.stats = {"DEX": 10}
        character.level = 1
        character.character_class_id = None

        # (10 * 3) + (1 * 2) = 30 + 2 = 32
        result = calculate_max_armor(character)

        assert result == 32.0

    def test_armor_scales_with_dexterity(self):
        """Test that armor scales with DEX stat."""
        character = MagicMock()
        character.stats = {"DEX": 20}
        character.level = 1
        character.character_class_id = None

        # (20 * 3) + (1 * 2) = 60 + 2 = 62
        result = calculate_max_armor(character)

        assert result == 62.0

    def test_armor_scales_with_level(self):
        """Test that armor increases with level."""
        character = MagicMock()
        character.stats = {"DEX": 10}
        character.level = 5
        character.character_class_id = None

        # (10 * 3) + (5 * 2) = 30 + 10 = 40
        result = calculate_max_armor(character)

        assert result == 40.0

    def test_armor_with_equipment_bonus(self):
        """Test that equipment bonuses are added to armor."""
        character = MagicMock()
        character.stats = {"DEX": 10}
        character.level = 1
        character.character_class_id = None

        equipment_bonuses = {"max_armor": 15.0}

        # Base: 32 + Equipment: 15 = 47
        result = calculate_max_armor(character, equipment_resource_bonuses=equipment_bonuses)

        assert result == 47.0

    def test_armor_with_high_dex_and_level(self):
        """Test armor calculation with high DEX and level."""
        character = MagicMock()
        character.stats = {"DEX": 25}
        character.level = 10
        character.character_class_id = None

        # (25 * 3) + (10 * 2) = 75 + 20 = 95
        result = calculate_max_armor(character)

        assert result == 95.0

    def test_handles_missing_dex_stat(self):
        """Test that missing DEX stat defaults to 0."""
        character = MagicMock()
        character.stats = {}
        character.level = 1
        character.character_class_id = None

        # (0 * 3) + (1 * 2) = 2
        result = calculate_max_armor(character)

        assert result == 2.0

    def test_class_does_not_affect_armor(self):
        """Test that character class does not add armor bonuses."""
        character = MagicMock()
        character.stats = {"DEX": 10}
        character.level = 1
        character.character_class_id = ENFORCER_ID

        # No class modifier for armor in current implementation
        # (10 * 3) + (1 * 2) = 32
        result = calculate_max_armor(character)

        assert result == 32.0


class TestAllClassesResourceCalculations:
    """Integration tests for all character classes."""

    def test_enforcer_resources_level_1(self):
        """Test all resources for Enforcer at level 1."""
        character = MagicMock()
        character.stats = {"STR": 15, "DEX": 12, "INT": 8}
        character.level = 1
        character.character_class_id = ENFORCER_ID

        health = calculate_max_health(character)
        stamina = calculate_max_stamina(character)
        tech_power = calculate_max_tech_power(character)
        armor = calculate_max_armor(character)

        # Health: (15*8) + (12*2) + (1*10) + 50 + (5*1) = 120 + 24 + 10 + 55 = 209
        assert health == 209.0
        # Stamina: (12*5) + (15*2) + (1*5) + 30 = 60 + 30 + 5 + 30 = 125
        assert stamina == 125.0
        # Tech Power: (8*10) + (1*8) + 10 = 80 + 8 + 10 = 98
        assert tech_power == 98.0
        # Armor: (12*3) + (1*2) = 36 + 2 = 38
        assert armor == 38.0

    def test_tech_wizard_resources_level_5(self):
        """Test all resources for Tech Wizard at level 5."""
        character = MagicMock()
        character.stats = {"STR": 8, "DEX": 10, "INT": 18}
        character.level = 5
        character.character_class_id = TECH_WIZARD_ID

        health = calculate_max_health(character)
        stamina = calculate_max_stamina(character)
        tech_power = calculate_max_tech_power(character)
        armor = calculate_max_armor(character)

        # Health: (8*8) + (10*2) + (5*10) + 20 = 64 + 20 + 50 + 20 = 154
        assert health == 154.0
        # Stamina: (10*5) + (8*2) + (5*5) + 15 = 50 + 16 + 25 + 15 = 106
        assert stamina == 106.0
        # Tech Power: (18*10) + (5*8) + 50 + (10*5) = 180 + 40 + 100 = 320
        assert tech_power == 320.0
        # Armor: (10*3) + (5*2) = 30 + 10 = 40
        assert armor == 40.0

    def test_all_resources_with_equipment_bonuses(self):
        """Test that all resources can have equipment bonuses."""
        character = MagicMock()
        character.stats = {"STR": 10, "DEX": 10, "INT": 10}
        character.level = 1
        character.character_class_id = None

        equipment_bonuses = {
            "max_health": 25.0,
            "max_stamina": 15.0,
            "max_tech_power": 20.0,
            "max_armor": 10.0,
        }

        health = calculate_max_health(character, equipment_resource_bonuses=equipment_bonuses)
        stamina = calculate_max_stamina(character, equipment_resource_bonuses=equipment_bonuses)
        tech_power = calculate_max_tech_power(character, equipment_resource_bonuses=equipment_bonuses)
        armor = calculate_max_armor(character, equipment_resource_bonuses=equipment_bonuses)

        # All should have bonuses added
        assert health == 135.0  # 110 + 25
        assert stamina == 90.0  # 75 + 15
        assert tech_power == 128.0  # 108 + 20
        assert armor == 42.0  # 32 + 10
