"""Tests for combat display formatting functions."""

import pytest
from unittest.mock import MagicMock

from ds_common.combat.display import format_resource_display, format_combat_status


class TestFormatResourceDisplay:
    """Tests for format_resource_display function."""

    def test_formats_all_resources_as_integers(self):
        """Test that all float resources are converted to integers."""
        character = MagicMock()
        character.current_health = 45.7
        character.max_health = 100.2
        character.current_stamina = 23.9
        character.max_stamina = 50.1
        character.current_tech_power = 12.3
        character.max_tech_power = 30.8
        character.current_armor = 8.6
        character.max_armor = 20.4
        character.is_incapacitated = False

        result = format_resource_display(character)

        assert result["current_health"] == 45
        assert result["max_health"] == 100
        assert result["current_stamina"] == 23
        assert result["max_stamina"] == 50
        assert result["current_tech_power"] == 12
        assert result["max_tech_power"] == 30
        assert result["current_armor"] == 8
        assert result["max_armor"] == 20
        assert result["is_incapacitated"] is False

    def test_handles_integer_values(self):
        """Test that integer values are preserved."""
        character = MagicMock()
        character.current_health = 50
        character.max_health = 100
        character.current_stamina = 25
        character.max_stamina = 50
        character.current_tech_power = 15
        character.max_tech_power = 30
        character.current_armor = 10
        character.max_armor = 20
        character.is_incapacitated = False

        result = format_resource_display(character)

        assert result["current_health"] == 50
        assert result["max_health"] == 100
        assert result["current_stamina"] == 25
        assert result["max_stamina"] == 50

    def test_handles_zero_values(self):
        """Test that zero values are handled correctly."""
        character = MagicMock()
        character.current_health = 0.0
        character.max_health = 100.0
        character.current_stamina = 0.0
        character.max_stamina = 50.0
        character.current_tech_power = 0.0
        character.max_tech_power = 30.0
        character.current_armor = 0.0
        character.max_armor = 20.0
        character.is_incapacitated = True

        result = format_resource_display(character)

        assert result["current_health"] == 0
        assert result["current_stamina"] == 0
        assert result["current_tech_power"] == 0
        assert result["current_armor"] == 0
        assert result["is_incapacitated"] is True

    def test_rounds_down_decimal_values(self):
        """Test that decimal values are truncated (not rounded)."""
        character = MagicMock()
        character.current_health = 99.9
        character.max_health = 100.9
        character.current_stamina = 49.9
        character.max_stamina = 50.9
        character.current_tech_power = 29.9
        character.max_tech_power = 30.9
        character.current_armor = 19.9
        character.max_armor = 20.9
        character.is_incapacitated = False

        result = format_resource_display(character)

        # int() truncates, doesn't round
        assert result["current_health"] == 99
        assert result["max_health"] == 100
        assert result["current_stamina"] == 49
        assert result["max_stamina"] == 50

    def test_includes_incapacitation_status(self):
        """Test that incapacitation status is included in result."""
        character = MagicMock()
        character.current_health = 0.0
        character.max_health = 100.0
        character.current_stamina = 25.0
        character.max_stamina = 50.0
        character.current_tech_power = 15.0
        character.max_tech_power = 30.0
        character.current_armor = 10.0
        character.max_armor = 20.0
        character.is_incapacitated = True

        result = format_resource_display(character)

        assert "is_incapacitated" in result
        assert result["is_incapacitated"] is True

    def test_works_with_npc(self):
        """Test that function works with NPC objects."""
        npc = MagicMock()
        npc.current_health = 80.5
        npc.max_health = 150.2
        npc.current_stamina = 40.3
        npc.max_stamina = 60.7
        npc.current_tech_power = 20.1
        npc.max_tech_power = 40.9
        npc.current_armor = 15.8
        npc.max_armor = 30.2
        npc.is_incapacitated = False

        result = format_resource_display(npc)

        assert result["current_health"] == 80
        assert result["max_health"] == 150


class TestFormatCombatStatus:
    """Tests for format_combat_status function."""

    def test_formats_basic_combat_status(self):
        """Test that combat status is formatted as expected."""
        character = MagicMock()
        character.current_health = 50.0
        character.max_health = 100.0
        character.current_stamina = 25.0
        character.max_stamina = 50.0
        character.current_tech_power = 15.0
        character.max_tech_power = 30.0
        character.current_armor = 10.0
        character.max_armor = 20.0
        character.is_incapacitated = False

        result = format_combat_status(character)

        assert "Health: 50/100" in result
        assert "Stamina: 25/50" in result
        assert "Tech Power: 15/30" in result
        assert "Armor: 10/20" in result
        assert " | " in result  # Pipe separator

    def test_includes_incapacitated_status(self):
        """Test that INCAPACITATED status is shown when character is incapacitated."""
        character = MagicMock()
        character.current_health = 0.0
        character.max_health = 100.0
        character.current_stamina = 0.0
        character.max_stamina = 50.0
        character.current_tech_power = 0.0
        character.max_tech_power = 30.0
        character.current_armor = 0.0
        character.max_armor = 20.0
        character.is_incapacitated = True

        result = format_combat_status(character)

        assert "Status: INCAPACITATED" in result

    def test_excludes_incapacitated_when_not_incapacitated(self):
        """Test that INCAPACITATED status is not shown for active characters."""
        character = MagicMock()
        character.current_health = 50.0
        character.max_health = 100.0
        character.current_stamina = 25.0
        character.max_stamina = 50.0
        character.current_tech_power = 15.0
        character.max_tech_power = 30.0
        character.current_armor = 10.0
        character.max_armor = 20.0
        character.is_incapacitated = False

        result = format_combat_status(character)

        assert "INCAPACITATED" not in result

    def test_uses_pipe_separator(self):
        """Test that status parts are separated by ' | '."""
        character = MagicMock()
        character.current_health = 100.0
        character.max_health = 100.0
        character.current_stamina = 50.0
        character.max_stamina = 50.0
        character.current_tech_power = 30.0
        character.max_tech_power = 30.0
        character.current_armor = 20.0
        character.max_armor = 20.0
        character.is_incapacitated = False

        result = format_combat_status(character)

        # Should have 3 pipe separators (between 4 resource sections)
        assert result.count(" | ") == 3

    def test_formats_floats_as_integers(self):
        """Test that float values are displayed as integers."""
        character = MagicMock()
        character.current_health = 45.7
        character.max_health = 100.9
        character.current_stamina = 23.3
        character.max_stamina = 50.8
        character.current_tech_power = 12.6
        character.max_tech_power = 30.2
        character.current_armor = 8.9
        character.max_armor = 20.1
        character.is_incapacitated = False

        result = format_combat_status(character)

        # Should show truncated integers
        assert "Health: 45/100" in result
        assert "Stamina: 23/50" in result
        assert "Tech Power: 12/30" in result
        assert "Armor: 8/20" in result

    def test_full_resources(self):
        """Test formatting when all resources are at maximum."""
        character = MagicMock()
        character.current_health = 100.0
        character.max_health = 100.0
        character.current_stamina = 50.0
        character.max_stamina = 50.0
        character.current_tech_power = 30.0
        character.max_tech_power = 30.0
        character.current_armor = 20.0
        character.max_armor = 20.0
        character.is_incapacitated = False

        result = format_combat_status(character)

        assert "Health: 100/100" in result
        assert "Stamina: 50/50" in result
        assert "Tech Power: 30/30" in result
        assert "Armor: 20/20" in result

    def test_depleted_resources(self):
        """Test formatting when all resources are depleted."""
        character = MagicMock()
        character.current_health = 0.0
        character.max_health = 100.0
        character.current_stamina = 0.0
        character.max_stamina = 50.0
        character.current_tech_power = 0.0
        character.max_tech_power = 30.0
        character.current_armor = 0.0
        character.max_armor = 20.0
        character.is_incapacitated = True

        result = format_combat_status(character)

        assert "Health: 0/100" in result
        assert "Stamina: 0/50" in result
        assert "Tech Power: 0/30" in result
        assert "Armor: 0/20" in result
        assert "INCAPACITATED" in result
