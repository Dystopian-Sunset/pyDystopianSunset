"""Tests for experience and leveling service."""

import pytest
from unittest.mock import MagicMock

from ds_common.combat.experience_service import (
    calculate_experience_reward,
    calculate_exp_for_level,
    add_experience,
    apply_level_up,
)


class TestCalculateExperienceReward:
    """Tests for calculate_experience_reward function."""

    def test_higher_level_npc_bonus_experience(self):
        """Test that fighting higher level NPCs grants bonus experience."""
        # Level 5 NPC vs Level 1 character
        # Formula: 100 * 5 * (1 + (5-1) * 0.1) = 500 * 1.4 = 700
        exp = calculate_experience_reward(npc_level=5, character_level=1)
        assert exp == 700

    def test_same_level_npc_base_experience(self):
        """Test that same level NPCs grant base experience."""
        # Level 3 NPC vs Level 3 character
        # Formula: 50 * 3 = 150
        exp = calculate_experience_reward(npc_level=3, character_level=3)
        assert exp == 150

    def test_lower_level_npc_base_experience(self):
        """Test that lower level NPCs grant base experience."""
        # Level 2 NPC vs Level 5 character
        # Formula: 50 * 2 = 100
        exp = calculate_experience_reward(npc_level=2, character_level=5)
        assert exp == 100

    def test_level_1_npc_minimum_experience(self):
        """Test that level 1 NPCs grant minimum experience."""
        # Level 1 NPC vs Level 1 character
        # Formula: 50 * 1 = 50
        exp = calculate_experience_reward(npc_level=1, character_level=1)
        assert exp == 50

    def test_much_higher_level_npc_large_bonus(self):
        """Test that much higher level NPCs grant large experience bonuses."""
        # Level 10 NPC vs Level 1 character
        # Formula: 100 * 10 * (1 + (10-1) * 0.1) = 1000 * 1.9 = 1900
        exp = calculate_experience_reward(npc_level=10, character_level=1)
        assert exp == 1900

    def test_experience_scales_with_npc_level(self):
        """Test that experience scales proportionally with NPC level."""
        # Level 4 NPC vs Level 4 character (same level)
        exp1 = calculate_experience_reward(npc_level=4, character_level=4)
        # Level 8 NPC vs Level 8 character (same level, double level)
        exp2 = calculate_experience_reward(npc_level=8, character_level=8)

        # Double the NPC level should double the experience (same level scenario)
        assert exp2 == exp1 * 2

    def test_minimum_experience_is_one(self):
        """Test that experience is always at least 1."""
        # Even if formula somehow produces 0 or negative, should be 1
        exp = calculate_experience_reward(npc_level=1, character_level=100)
        assert exp >= 1


class TestCalculateExpForLevel:
    """Tests for calculate_exp_for_level function."""

    def test_level_1_requires_zero_exp(self):
        """Test that level 1 (starting level) requires 0 experience."""
        exp = calculate_exp_for_level(1)
        assert exp == 0

    def test_level_2_requires_4000_exp(self):
        """Test that level 2 requires 4000 experience."""
        # Formula: 1000 * (2 ** 2) = 4000
        exp = calculate_exp_for_level(2)
        assert exp == 4000

    def test_level_3_requires_9000_exp(self):
        """Test that level 3 requires 9000 experience."""
        # Formula: 1000 * (3 ** 2) = 9000
        exp = calculate_exp_for_level(3)
        assert exp == 9000

    def test_level_4_requires_16000_exp(self):
        """Test that level 4 requires 16000 experience."""
        # Formula: 1000 * (4 ** 2) = 16000
        exp = calculate_exp_for_level(4)
        assert exp == 16000

    def test_level_10_requires_100000_exp(self):
        """Test that level 10 requires 100000 experience."""
        # Formula: 1000 * (10 ** 2) = 100000
        exp = calculate_exp_for_level(10)
        assert exp == 100000

    def test_level_0_returns_zero(self):
        """Test that level 0 or below returns 0 experience."""
        assert calculate_exp_for_level(0) == 0
        assert calculate_exp_for_level(-1) == 0

    def test_exponential_growth(self):
        """Test that experience requirements grow exponentially."""
        exp_level_2 = calculate_exp_for_level(2)
        exp_level_4 = calculate_exp_for_level(4)

        # Level 4 should require 4x the experience of level 2
        # (4^2) / (2^2) = 16/4 = 4
        assert exp_level_4 == exp_level_2 * 4


class TestAddExperience:
    """Tests for add_experience function."""

    def test_add_experience_increases_character_exp(self):
        """Test that adding experience increases character's exp."""
        character = MagicMock()
        character.name = "Test"
        character.level = 1
        character.exp = 0

        updated_char, leveled_up = add_experience(character, 100)

        assert updated_char.exp == 100
        assert leveled_up is False

    def test_add_experience_no_level_up_below_threshold(self):
        """Test that character doesn't level up below experience threshold."""
        character = MagicMock()
        character.name = "Test"
        character.level = 1
        character.exp = 0

        # Need 4000 exp for level 2, add only 3000
        updated_char, leveled_up = add_experience(character, 3000)

        assert updated_char.exp == 3000
        assert updated_char.level == 1
        assert leveled_up is False

    def test_add_experience_triggers_level_up(self):
        """Test that character levels up when reaching threshold."""
        character = MagicMock()
        character.name = "Test"
        character.level = 1
        character.exp = 0

        # Need 4000 exp for level 2
        updated_char, leveled_up = add_experience(character, 4000)

        assert updated_char.exp == 4000
        assert updated_char.level == 2
        assert leveled_up is True

    def test_add_experience_multiple_level_ups(self):
        """Test that character can level up multiple times from one exp gain."""
        character = MagicMock()
        character.name = "Test"
        character.level = 1
        character.exp = 0

        # Add enough exp to go from level 1 to level 3
        # Level 2: 4000, Level 3: 9000
        updated_char, leveled_up = add_experience(character, 10000)

        assert updated_char.exp == 10000
        assert updated_char.level == 3
        assert leveled_up is True

    def test_add_experience_accumulates_existing_exp(self):
        """Test that experience accumulates on top of existing exp."""
        character = MagicMock()
        character.name = "Test"
        character.level = 1
        character.exp = 2000

        updated_char, leveled_up = add_experience(character, 2500)

        # Should have 4500 total, which is enough for level 2 (4000)
        assert updated_char.exp == 4500
        assert updated_char.level == 2
        assert leveled_up is True

    def test_add_zero_experience_no_change(self):
        """Test that adding 0 experience makes no changes."""
        character = MagicMock()
        character.name = "Test"
        character.level = 1
        character.exp = 1000

        updated_char, leveled_up = add_experience(character, 0)

        assert updated_char.exp == 1000
        assert updated_char.level == 1
        assert leveled_up is False

    def test_add_negative_experience_no_change(self):
        """Test that adding negative experience makes no changes."""
        character = MagicMock()
        character.name = "Test"
        character.level = 1
        character.exp = 1000

        updated_char, leveled_up = add_experience(character, -500)

        assert updated_char.exp == 1000
        assert updated_char.level == 1
        assert leveled_up is False


class TestApplyLevelUp:
    """Tests for apply_level_up function."""

    def test_apply_level_up_increases_all_stats(self):
        """Test that level up increases all stats by 2."""
        character = MagicMock()
        character.name = "Test"
        character.stats = {
            "STR": 10,
            "DEX": 10,
            "INT": 10,
            "PER": 10,
            "CHA": 10,
            "LUK": 10,
        }

        updated_char = apply_level_up(character)

        assert updated_char.stats["STR"] == 12
        assert updated_char.stats["DEX"] == 12
        assert updated_char.stats["INT"] == 12
        assert updated_char.stats["PER"] == 12
        assert updated_char.stats["CHA"] == 12
        assert updated_char.stats["LUK"] == 12

    def test_apply_level_up_with_existing_high_stats(self):
        """Test that level up correctly adds to already high stats."""
        character = MagicMock()
        character.name = "Test"
        character.stats = {
            "STR": 25,
            "DEX": 18,
            "INT": 30,
            "PER": 15,
            "CHA": 20,
            "LUK": 12,
        }

        updated_char = apply_level_up(character)

        assert updated_char.stats["STR"] == 27
        assert updated_char.stats["DEX"] == 20
        assert updated_char.stats["INT"] == 32
        assert updated_char.stats["PER"] == 17
        assert updated_char.stats["CHA"] == 22
        assert updated_char.stats["LUK"] == 14

    def test_apply_level_up_handles_missing_stats(self):
        """Test that level up handles characters with missing stats."""
        character = MagicMock()
        character.name = "Test"
        character.stats = {
            "STR": 10,
            # Missing other stats
        }

        updated_char = apply_level_up(character)

        # Should have STR increased, others should be set to 2 (0 + 2)
        assert updated_char.stats["STR"] == 12
        assert updated_char.stats.get("DEX", 0) == 2
        assert updated_char.stats.get("INT", 0) == 2
        assert updated_char.stats.get("PER", 0) == 2
        assert updated_char.stats.get("CHA", 0) == 2
        assert updated_char.stats.get("LUK", 0) == 2

    def test_apply_level_up_returns_character(self):
        """Test that apply_level_up returns the character object."""
        character = MagicMock()
        character.name = "Test"
        character.stats = {"STR": 10, "DEX": 10, "INT": 10, "PER": 10, "CHA": 10, "LUK": 10}

        result = apply_level_up(character)

        assert result is character
