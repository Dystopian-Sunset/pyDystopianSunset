"""
Damage and resource management service.
"""

from typing import TYPE_CHECKING

from ds_common.combat.models import CombatResult, DamageType

if TYPE_CHECKING:
    from ds_common.models.character import Character
    from ds_common.models.npc import NPC


def apply_damage(
    character: "Character | NPC",
    damage_amount: float,
    damage_type: DamageType = DamageType.PHYSICAL,
) -> CombatResult:
    """
    Apply damage to a character. Armor is reduced first, then health.

    Args:
        character: Character or NPC to apply damage to
        damage_amount: Amount of damage to apply
        damage_type: Type of damage (affects armor absorption)

    Returns:
        CombatResult with before/after states
    """
    before_health = character.current_health
    before_armor = character.current_armor

    remaining_damage = damage_amount

    # Reduce armor first
    if character.current_armor > 0:
        armor_damage = min(remaining_damage, character.current_armor)
        character.current_armor -= armor_damage
        remaining_damage -= armor_damage

    # Apply remaining damage to health
    if remaining_damage > 0:
        character.current_health = max(0.0, character.current_health - remaining_damage)

    after_health = character.current_health
    after_armor = character.current_armor

    # Check incapacitation
    is_incapacitated = character.current_health <= 0.0
    if is_incapacitated:
        character.is_incapacitated = True

    message = f"Took {damage_amount:.1f} {damage_type.value} damage"
    if before_armor > 0:
        message += f" ({before_armor - after_armor:.1f} to armor, {remaining_damage:.1f} to health)"

    return CombatResult(
        character=character,
        before_health=before_health,
        after_health=after_health,
        before_armor=before_armor,
        after_armor=after_armor,
        message=message,
        is_incapacitated=is_incapacitated,
    )


def apply_healing(character: "Character | NPC", heal_amount: float) -> CombatResult:
    """
    Apply healing to a character. Health is restored up to max_health.

    Args:
        character: Character or NPC to heal
        heal_amount: Amount of health to restore

    Returns:
        CombatResult with before/after states
    """
    before_health = character.current_health
    character.current_health = min(character.max_health, character.current_health + heal_amount)
    after_health = character.current_health

    # If health is restored above 0, character is no longer incapacitated
    if character.current_health > 0.0:
        character.is_incapacitated = False

    actual_healed = after_health - before_health
    message = f"Healed {actual_healed:.1f} health"

    return CombatResult(
        character=character,
        before_health=before_health,
        after_health=after_health,
        message=message,
        is_incapacitated=character.is_incapacitated,
    )


def consume_stamina(character: "Character | NPC", amount: float) -> bool:
    """
    Consume stamina from a character.

    Args:
        character: Character or NPC
        amount: Amount of stamina to consume

    Returns:
        True if successful, False if not enough stamina
    """
    if character.current_stamina >= amount:
        character.current_stamina -= amount
        return True
    return False


def consume_tech_power(character: "Character | NPC", amount: float) -> bool:
    """
    Consume tech power from a character.

    Args:
        character: Character or NPC
        amount: Amount of tech power to consume

    Returns:
        True if successful, False if not enough tech power
    """
    if character.current_tech_power >= amount:
        character.current_tech_power -= amount
        return True
    return False


def restore_stamina(character: "Character | NPC", amount: float) -> CombatResult:
    """
    Restore stamina to a character. Stamina is restored up to max_stamina.

    Args:
        character: Character or NPC
        amount: Amount of stamina to restore

    Returns:
        CombatResult with before/after states
    """
    before_stamina = character.current_stamina
    character.current_stamina = min(character.max_stamina, character.current_stamina + amount)
    after_stamina = character.current_stamina

    message = f"Restored {after_stamina - before_stamina:.1f} stamina"

    return CombatResult(
        character=character,
        before_health=character.current_health,
        after_health=character.current_health,
        before_stamina=before_stamina,
        after_stamina=after_stamina,
        message=message,
    )


def restore_tech_power(character: "Character | NPC", amount: float) -> CombatResult:
    """
    Restore tech power to a character. Tech power is restored up to max_tech_power.

    Args:
        character: Character or NPC
        amount: Amount of tech power to restore

    Returns:
        CombatResult with before/after states
    """
    before_tech_power = character.current_tech_power
    character.current_tech_power = min(
        character.max_tech_power, character.current_tech_power + amount
    )
    after_tech_power = character.current_tech_power

    message = f"Restored {after_tech_power - before_tech_power:.1f} tech power"

    return CombatResult(
        character=character,
        before_health=character.current_health,
        after_health=character.current_health,
        before_tech_power=before_tech_power,
        after_tech_power=after_tech_power,
        message=message,
    )


def update_armor(character: "Character | NPC", amount: float) -> CombatResult:
    """
    Update armor on a character. Can be positive (restore) or negative (damage).

    Args:
        character: Character or NPC
        amount: Amount to change armor by (positive = restore, negative = damage)

    Returns:
        CombatResult with before/after states
    """
    before_armor = character.current_armor
    character.current_armor = max(0.0, min(character.max_armor, character.current_armor + amount))
    after_armor = character.current_armor

    if amount > 0:
        message = f"Restored {after_armor - before_armor:.1f} armor"
    else:
        message = f"Lost {before_armor - after_armor:.1f} armor"

    return CombatResult(
        character=character,
        before_health=character.current_health,
        after_health=character.current_health,
        before_armor=before_armor,
        after_armor=after_armor,
        message=message,
    )


def check_incapacitation(character: "Character | NPC") -> bool:
    """
    Check if a character should be incapacitated.

    Args:
        character: Character or NPC to check

    Returns:
        True if character is incapacitated
    """
    is_incapacitated = character.current_health <= 0.0
    character.is_incapacitated = is_incapacitated
    return is_incapacitated
