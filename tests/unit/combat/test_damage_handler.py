"""Tests for damage handler functions."""

import pytest
from unittest.mock import MagicMock

from ds_common.combat.damage_handler import (
    apply_damage,
    apply_healing,
    consume_stamina,
    consume_tech_power,
    restore_stamina,
    restore_tech_power,
    update_armor,
    check_incapacitation,
)
from ds_common.combat.models import DamageType


class TestApplyDamage:
    """Tests for apply_damage function."""

    def test_damage_to_armor_only(self):
        """Test that damage reduces armor first if available."""
        character = MagicMock()
        character.current_health = 100.0
        character.current_armor = 50.0
        character.is_incapacitated = False

        result = apply_damage(character, 30.0)

        # Should reduce armor by 30, health unchanged
        assert character.current_armor == 20.0
        assert character.current_health == 100.0
        assert result.before_armor == 50.0
        assert result.after_armor == 20.0
        assert result.before_health == 100.0
        assert result.after_health == 100.0
        assert result.is_incapacitated is False

    def test_damage_exceeds_armor(self):
        """Test that damage overflow goes to health after armor is depleted."""
        character = MagicMock()
        character.current_health = 100.0
        character.current_armor = 20.0
        character.is_incapacitated = False

        result = apply_damage(character, 50.0)

        # 20 to armor, 30 to health
        assert character.current_armor == 0.0
        assert character.current_health == 70.0
        assert result.before_armor == 20.0
        assert result.after_armor == 0.0
        assert result.before_health == 100.0
        assert result.after_health == 70.0
        assert result.is_incapacitated is False

    def test_damage_to_health_only(self):
        """Test damage when character has no armor."""
        character = MagicMock()
        character.current_health = 100.0
        character.current_armor = 0.0
        character.is_incapacitated = False

        result = apply_damage(character, 40.0)

        assert character.current_armor == 0.0
        assert character.current_health == 60.0
        assert result.after_health == 60.0
        assert result.is_incapacitated is False

    def test_damage_causes_incapacitation(self):
        """Test that reducing health to 0 causes incapacitation."""
        character = MagicMock()
        character.current_health = 50.0
        character.current_armor = 0.0
        character.is_incapacitated = False

        result = apply_damage(character, 50.0)

        assert character.current_health == 0.0
        assert character.is_incapacitated is True
        assert result.is_incapacitated is True

    def test_overkill_damage(self):
        """Test that damage exceeding health caps at 0."""
        character = MagicMock()
        character.current_health = 30.0
        character.current_armor = 0.0
        character.is_incapacitated = False

        result = apply_damage(character, 100.0)

        # Health should be 0, not negative
        assert character.current_health == 0.0
        assert character.is_incapacitated is True
        assert result.after_health == 0.0

    def test_damage_type_parameter(self):
        """Test that damage type is included in result message."""
        character = MagicMock()
        character.current_health = 100.0
        character.current_armor = 50.0
        character.is_incapacitated = False

        result = apply_damage(character, 30.0, damage_type=DamageType.TECH)

        assert "tech" in result.message
        assert "30.0" in result.message

    def test_zero_damage(self):
        """Test applying zero damage."""
        character = MagicMock()
        character.current_health = 100.0
        character.current_armor = 50.0
        character.is_incapacitated = False

        result = apply_damage(character, 0.0)

        assert character.current_health == 100.0
        assert character.current_armor == 50.0
        assert result.is_incapacitated is False


class TestApplyHealing:
    """Tests for apply_healing function."""

    def test_basic_healing(self):
        """Test basic healing increases health."""
        character = MagicMock()
        character.current_health = 50.0
        character.max_health = 100.0
        character.is_incapacitated = False

        result = apply_healing(character, 30.0)

        assert character.current_health == 80.0
        assert result.before_health == 50.0
        assert result.after_health == 80.0
        assert "30.0" in result.message

    def test_healing_capped_at_max_health(self):
        """Test that healing cannot exceed max_health."""
        character = MagicMock()
        character.current_health = 80.0
        character.max_health = 100.0
        character.is_incapacitated = False

        result = apply_healing(character, 50.0)

        # Should cap at 100, not go to 130
        assert character.current_health == 100.0
        assert result.after_health == 100.0
        # Message should show actual healed amount (20)
        assert "20.0" in result.message

    def test_healing_removes_incapacitation(self):
        """Test that healing above 0 removes incapacitation."""
        character = MagicMock()
        character.current_health = 0.0
        character.max_health = 100.0
        character.is_incapacitated = True

        result = apply_healing(character, 30.0)

        assert character.current_health == 30.0
        assert character.is_incapacitated is False
        assert result.is_incapacitated is False

    def test_healing_at_full_health(self):
        """Test healing when already at full health."""
        character = MagicMock()
        character.current_health = 100.0
        character.max_health = 100.0
        character.is_incapacitated = False

        result = apply_healing(character, 20.0)

        assert character.current_health == 100.0
        # Should show 0 healing
        assert "0.0" in result.message

    def test_zero_healing(self):
        """Test applying zero healing."""
        character = MagicMock()
        character.current_health = 50.0
        character.max_health = 100.0
        character.is_incapacitated = False

        result = apply_healing(character, 0.0)

        assert character.current_health == 50.0
        assert result.after_health == 50.0


class TestConsumeStamina:
    """Tests for consume_stamina function."""

    def test_consume_stamina_success(self):
        """Test successful stamina consumption."""
        character = MagicMock()
        character.current_stamina = 50.0

        result = consume_stamina(character, 20.0)

        assert result is True
        assert character.current_stamina == 30.0

    def test_consume_stamina_exact_amount(self):
        """Test consuming exact amount of stamina available."""
        character = MagicMock()
        character.current_stamina = 30.0

        result = consume_stamina(character, 30.0)

        assert result is True
        assert character.current_stamina == 0.0

    def test_consume_stamina_insufficient(self):
        """Test that consumption fails when not enough stamina."""
        character = MagicMock()
        character.current_stamina = 10.0

        result = consume_stamina(character, 20.0)

        assert result is False
        # Stamina should be unchanged
        assert character.current_stamina == 10.0

    def test_consume_zero_stamina(self):
        """Test consuming zero stamina."""
        character = MagicMock()
        character.current_stamina = 50.0

        result = consume_stamina(character, 0.0)

        assert result is True
        assert character.current_stamina == 50.0

    def test_consume_stamina_when_empty(self):
        """Test consuming stamina when none available."""
        character = MagicMock()
        character.current_stamina = 0.0

        result = consume_stamina(character, 10.0)

        assert result is False
        assert character.current_stamina == 0.0


class TestConsumeTechPower:
    """Tests for consume_tech_power function."""

    def test_consume_tech_power_success(self):
        """Test successful tech power consumption."""
        character = MagicMock()
        character.current_tech_power = 50.0

        result = consume_tech_power(character, 20.0)

        assert result is True
        assert character.current_tech_power == 30.0

    def test_consume_tech_power_exact_amount(self):
        """Test consuming exact amount of tech power available."""
        character = MagicMock()
        character.current_tech_power = 30.0

        result = consume_tech_power(character, 30.0)

        assert result is True
        assert character.current_tech_power == 0.0

    def test_consume_tech_power_insufficient(self):
        """Test that consumption fails when not enough tech power."""
        character = MagicMock()
        character.current_tech_power = 10.0

        result = consume_tech_power(character, 20.0)

        assert result is False
        # Tech power should be unchanged
        assert character.current_tech_power == 10.0

    def test_consume_zero_tech_power(self):
        """Test consuming zero tech power."""
        character = MagicMock()
        character.current_tech_power = 50.0

        result = consume_tech_power(character, 0.0)

        assert result is True
        assert character.current_tech_power == 50.0


class TestRestoreStamina:
    """Tests for restore_stamina function."""

    def test_restore_stamina_basic(self):
        """Test basic stamina restoration."""
        character = MagicMock()
        character.current_stamina = 30.0
        character.max_stamina = 100.0
        character.current_health = 100.0

        result = restore_stamina(character, 20.0)

        assert character.current_stamina == 50.0
        assert result.before_stamina == 30.0
        assert result.after_stamina == 50.0
        assert "20.0" in result.message

    def test_restore_stamina_capped_at_max(self):
        """Test that stamina restoration caps at max_stamina."""
        character = MagicMock()
        character.current_stamina = 80.0
        character.max_stamina = 100.0
        character.current_health = 100.0

        result = restore_stamina(character, 50.0)

        # Should cap at 100, not 130
        assert character.current_stamina == 100.0
        # Message should show actual restored (20)
        assert "20.0" in result.message

    def test_restore_stamina_when_full(self):
        """Test restoring stamina when already at max."""
        character = MagicMock()
        character.current_stamina = 100.0
        character.max_stamina = 100.0
        character.current_health = 100.0

        result = restore_stamina(character, 20.0)

        assert character.current_stamina == 100.0
        # Should show 0 restored
        assert "0.0" in result.message


class TestRestoreTechPower:
    """Tests for restore_tech_power function."""

    def test_restore_tech_power_basic(self):
        """Test basic tech power restoration."""
        character = MagicMock()
        character.current_tech_power = 30.0
        character.max_tech_power = 100.0
        character.current_health = 100.0

        result = restore_tech_power(character, 20.0)

        assert character.current_tech_power == 50.0
        assert result.before_tech_power == 30.0
        assert result.after_tech_power == 50.0
        assert "20.0" in result.message

    def test_restore_tech_power_capped_at_max(self):
        """Test that tech power restoration caps at max_tech_power."""
        character = MagicMock()
        character.current_tech_power = 80.0
        character.max_tech_power = 100.0
        character.current_health = 100.0

        result = restore_tech_power(character, 50.0)

        # Should cap at 100
        assert character.current_tech_power == 100.0
        # Message should show actual restored (20)
        assert "20.0" in result.message

    def test_restore_tech_power_when_full(self):
        """Test restoring tech power when already at max."""
        character = MagicMock()
        character.current_tech_power = 100.0
        character.max_tech_power = 100.0
        character.current_health = 100.0

        result = restore_tech_power(character, 20.0)

        assert character.current_tech_power == 100.0
        # Should show 0 restored
        assert "0.0" in result.message


class TestUpdateArmor:
    """Tests for update_armor function."""

    def test_restore_armor(self):
        """Test restoring armor (positive amount)."""
        character = MagicMock()
        character.current_armor = 30.0
        character.max_armor = 100.0
        character.current_health = 100.0

        result = update_armor(character, 20.0)

        assert character.current_armor == 50.0
        assert result.before_armor == 30.0
        assert result.after_armor == 50.0
        assert "Restored" in result.message
        assert "20.0" in result.message

    def test_damage_armor(self):
        """Test damaging armor (negative amount)."""
        character = MagicMock()
        character.current_armor = 50.0
        character.max_armor = 100.0
        character.current_health = 100.0

        result = update_armor(character, -20.0)

        assert character.current_armor == 30.0
        assert result.before_armor == 50.0
        assert result.after_armor == 30.0
        assert "Lost" in result.message
        assert "20.0" in result.message

    def test_restore_armor_capped_at_max(self):
        """Test that armor restoration caps at max_armor."""
        character = MagicMock()
        character.current_armor = 80.0
        character.max_armor = 100.0
        character.current_health = 100.0

        result = update_armor(character, 50.0)

        # Should cap at 100
        assert character.current_armor == 100.0
        # Should show actual restored (20)
        assert "20.0" in result.message

    def test_damage_armor_capped_at_zero(self):
        """Test that armor damage caps at 0."""
        character = MagicMock()
        character.current_armor = 20.0
        character.max_armor = 100.0
        character.current_health = 100.0

        result = update_armor(character, -50.0)

        # Should cap at 0, not go negative
        assert character.current_armor == 0.0
        # Should show actual lost (20)
        assert "20.0" in result.message

    def test_update_armor_by_zero(self):
        """Test updating armor by 0."""
        character = MagicMock()
        character.current_armor = 50.0
        character.max_armor = 100.0
        character.current_health = 100.0

        result = update_armor(character, 0.0)

        assert character.current_armor == 50.0
        # Message might say "Restored 0.0" or "Lost 0.0"


class TestCheckIncapacitation:
    """Tests for check_incapacitation function."""

    def test_check_incapacitation_healthy(self):
        """Test checking incapacitation on healthy character."""
        character = MagicMock()
        character.current_health = 50.0

        result = check_incapacitation(character)

        assert result is False
        assert character.is_incapacitated is False

    def test_check_incapacitation_at_zero_health(self):
        """Test checking incapacitation when health is 0."""
        character = MagicMock()
        character.current_health = 0.0

        result = check_incapacitation(character)

        assert result is True
        assert character.is_incapacitated is True

    def test_check_incapacitation_negative_health(self):
        """Test checking incapacitation with negative health."""
        character = MagicMock()
        character.current_health = -10.0

        result = check_incapacitation(character)

        assert result is True
        assert character.is_incapacitated is True

    def test_check_incapacitation_at_full_health(self):
        """Test checking incapacitation at full health."""
        character = MagicMock()
        character.current_health = 100.0

        result = check_incapacitation(character)

        assert result is False
        assert character.is_incapacitated is False

    def test_check_incapacitation_low_but_not_zero(self):
        """Test checking incapacitation with very low but non-zero health."""
        character = MagicMock()
        character.current_health = 0.1

        result = check_incapacitation(character)

        assert result is False
        assert character.is_incapacitated is False
