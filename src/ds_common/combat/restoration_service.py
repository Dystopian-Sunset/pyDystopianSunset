"""
Stat restoration service for calculating and applying resource restoration over time.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from ds_common.combat.models import RestorationModifiers, RestorationRates, RestorationResult

if TYPE_CHECKING:
    from ds_common.models.character import Character
    from ds_common.models.character_class import CharacterClass
    from ds_common.models.item_template import ItemTemplate
    from ds_common.models.npc import NPC

# Character class IDs from seed data
ENFORCER_ID = UUID("00000000-0000-0000-0000-000000000001")
TECH_WIZARD_ID = UUID("00000000-0000-0000-0000-000000000002")
SMOOTH_TALKER_ID = UUID("00000000-0000-0000-0000-000000000003")
SPY_ID = UUID("00000000-0000-0000-0000-000000000004")
WILD_CARD_ID = UUID("00000000-0000-0000-0000-000000000005")


def _get_class_restoration_modifiers(
    character_class_id: UUID | None, level: int
) -> dict[str, float]:
    """
    Get class-specific restoration rate modifiers.

    Args:
        character_class_id: Character class UUID
        level: Character level

    Returns:
        Dictionary with restoration rate modifiers per resource
    """
    if character_class_id == ENFORCER_ID:
        return {
            "health_base": 0.3,
            "stamina_base": 0.2,
            "tech_power_base": 0.05,
            "armor_base": 0.0,
        }
    if character_class_id == TECH_WIZARD_ID:
        return {
            "health_base": 0.1,
            "stamina_base": 0.1,
            "tech_power_base": 0.5 + (0.1 * level),
            "armor_base": 0.0,
        }
    if character_class_id == SMOOTH_TALKER_ID:
        return {
            "health_base": 0.15,
            "stamina_base": 0.15,
            "tech_power_base": 0.2,
            "armor_base": 0.0,
        }
    if character_class_id == SPY_ID:
        return {
            "health_base": 0.12,
            "stamina_base": 0.25,
            "tech_power_base": 0.15,
            "armor_base": 0.0,
        }
    if character_class_id == WILD_CARD_ID:
        return {
            "health_base": 0.18,
            "stamina_base": 0.18,
            "tech_power_base": 0.25,
            "armor_base": 0.0,
        }
    return {
        "health_base": 0.0,
        "stamina_base": 0.0,
        "tech_power_base": 0.0,
        "armor_base": 0.0,
    }


def calculate_equipment_restoration_modifiers(
    character: "Character | NPC",
    equipped_templates: list["ItemTemplate"] | None = None,
) -> RestorationModifiers:
    """
    Scan character inventory for equipped items that modify restoration rates.
    Uses item templates if provided, otherwise falls back to direct item properties.

    Args:
        character: Character or NPC to check
        equipped_templates: Optional pre-loaded list of equipped item templates

    Returns:
        RestorationModifiers with equipment bonuses and multipliers
    """

    modifiers = RestorationModifiers()

    if not hasattr(character, "inventory") or not character.inventory:
        return modifiers

    # Process equipped items
    for item in character.inventory:
        if not isinstance(item, dict):
            continue

        # Check if item is equipped (could be a flag or in equipment slot)
        is_equipped = item.get("equipped", False) or item.get("equipment_slot") is not None

        if not is_equipped:
            continue

        # Try to get modifiers from item template first
        item_template_id = item.get("item_template_id")
        template = None
        if item_template_id and equipped_templates:
            for t in equipped_templates:
                if str(t.id) == str(item_template_id):
                    template = t
                    break

        if template and template.resource_regeneration_modifiers:
            # Use template modifiers
            regen_mods = template.resource_regeneration_modifiers

            # Health modifiers
            if "health" in regen_mods:
                health_mod = regen_mods["health"]
                if "bonus" in health_mod:
                    modifiers.health_bonus += float(health_mod["bonus"])
                if "multiplier" in health_mod:
                    modifiers.health_multiplier *= float(health_mod["multiplier"])

            # Stamina modifiers
            if "stamina" in regen_mods:
                stamina_mod = regen_mods["stamina"]
                if "bonus" in stamina_mod:
                    modifiers.stamina_bonus += float(stamina_mod["bonus"])
                if "multiplier" in stamina_mod:
                    modifiers.stamina_multiplier *= float(stamina_mod["multiplier"])

            # Tech power modifiers
            if "tech_power" in regen_mods:
                tech_mod = regen_mods["tech_power"]
                if "bonus" in tech_mod:
                    modifiers.tech_power_bonus += float(tech_mod["bonus"])
                if "multiplier" in tech_mod:
                    modifiers.tech_power_multiplier *= float(tech_mod["multiplier"])

            # Armor modifiers
            if "armor" in regen_mods:
                armor_mod = regen_mods["armor"]
                if "bonus" in armor_mod:
                    modifiers.armor_bonus += float(armor_mod["bonus"])
                if "multiplier" in armor_mod:
                    modifiers.armor_multiplier *= float(armor_mod["multiplier"])

        # Fall back to direct item properties (backward compatibility)
        # Health modifiers
        if "health_restoration_bonus" in item:
            modifiers.health_bonus += float(item["health_restoration_bonus"])
        if "health_restoration_multiplier" in item:
            modifiers.health_multiplier *= float(item["health_restoration_multiplier"])

        # Stamina modifiers
        if "stamina_restoration_bonus" in item:
            modifiers.stamina_bonus += float(item["stamina_restoration_bonus"])
        if "stamina_restoration_multiplier" in item:
            modifiers.stamina_multiplier *= float(item["stamina_restoration_multiplier"])

        # Tech power modifiers
        if "tech_power_restoration_bonus" in item:
            modifiers.tech_power_bonus += float(item["tech_power_restoration_bonus"])
        if "tech_power_restoration_multiplier" in item:
            modifiers.tech_power_multiplier *= float(item["tech_power_restoration_multiplier"])

        # Armor modifiers
        if "armor_restoration_bonus" in item:
            modifiers.armor_bonus += float(item["armor_restoration_bonus"])
        if "armor_restoration_multiplier" in item:
            modifiers.armor_multiplier *= float(item["armor_restoration_multiplier"])

    return modifiers


def calculate_buff_restoration_modifiers(character: "Character | NPC") -> RestorationModifiers:
    """
    Scan character effects dict for buffs/debuffs that modify restoration rates.

    Args:
        character: Character or NPC to check

    Returns:
        RestorationModifiers with buff bonuses and multipliers
    """
    modifiers = RestorationModifiers()

    if not hasattr(character, "effects") or not character.effects:
        return modifiers

    # Sum all bonuses and multiply all multipliers from effects
    for key, value in character.effects.items():
        if not isinstance(value, (int, float)):
            continue

        float_value = float(value)

        # Health modifiers
        if key == "health_restoration_bonus":
            modifiers.health_bonus += float_value
        elif key == "health_restoration_multiplier":
            modifiers.health_multiplier *= float_value

        # Stamina modifiers
        elif key == "stamina_restoration_bonus":
            modifiers.stamina_bonus += float_value
        elif key == "stamina_restoration_multiplier":
            modifiers.stamina_multiplier *= float_value

        # Tech power modifiers
        elif key == "tech_power_restoration_bonus":
            modifiers.tech_power_bonus += float_value
        elif key == "tech_power_restoration_multiplier":
            modifiers.tech_power_multiplier *= float_value

        # Armor modifiers
        elif key == "armor_restoration_bonus":
            modifiers.armor_bonus += float_value
        elif key == "armor_restoration_multiplier":
            modifiers.armor_multiplier *= float_value

    return modifiers


def apply_restoration_modifiers(
    base_rates: RestorationRates,
    equipment_mods: RestorationModifiers,
    buff_mods: RestorationModifiers,
) -> RestorationRates:
    """
    Combine base restoration rates with equipment and buff modifiers.

    Formula: ((base_rate + equipment_bonus) * equipment_multiplier + buff_bonus) * buff_multiplier

    Args:
        base_rates: Base restoration rates from stats
        equipment_mods: Equipment modifiers
        buff_mods: Buff/debuff modifiers

    Returns:
        Final restoration rates after applying all modifiers
    """
    # Health: ((base + equip_bonus) * equip_mult + buff_bonus) * buff_mult
    health = (
        (base_rates.health_per_second + equipment_mods.health_bonus)
        * equipment_mods.health_multiplier
        + buff_mods.health_bonus
    ) * buff_mods.health_multiplier

    # Stamina: same formula
    stamina = (
        (base_rates.stamina_per_second + equipment_mods.stamina_bonus)
        * equipment_mods.stamina_multiplier
        + buff_mods.stamina_bonus
    ) * buff_mods.stamina_multiplier

    # Tech power: same formula
    tech_power = (
        (base_rates.tech_power_per_second + equipment_mods.tech_power_bonus)
        * equipment_mods.tech_power_multiplier
        + buff_mods.tech_power_bonus
    ) * buff_mods.tech_power_multiplier

    # Armor: same formula
    armor = (
        (base_rates.armor_per_second + equipment_mods.armor_bonus) * equipment_mods.armor_multiplier
        + buff_mods.armor_bonus
    ) * buff_mods.armor_multiplier

    return RestorationRates(
        health_per_second=max(0.0, health),
        stamina_per_second=max(0.0, stamina),
        tech_power_per_second=max(0.0, tech_power),
        armor_per_second=max(0.0, armor),
    )


def calculate_restoration_rates(
    character: "Character | NPC", character_class: "CharacterClass | None" = None
) -> RestorationRates:
    """
    Calculate per-second restoration rates for each resource, factoring in equipment and buff effects.

    Args:
        character: Character or NPC
        character_class: Optional character class (for characters)

    Returns:
        RestorationRates with final calculated rates per second
    """
    stats = character.stats
    str_val = float(stats.get("STR", 0))
    dex_val = float(stats.get("DEX", 0))
    int_val = float(stats.get("INT", 0))
    level = float(character.level)

    class_id = character.character_class_id if hasattr(character, "character_class_id") else None
    class_mods = _get_class_restoration_modifiers(class_id, character.level)

    # Calculate base rates from stats
    base_health = (str_val * 0.1) + (level * 0.5) + class_mods["health_base"]
    base_stamina = (dex_val * 0.15) + (str_val * 0.05) + (level * 0.3) + class_mods["stamina_base"]
    base_tech_power = (int_val * 0.2) + (level * 0.4) + class_mods["tech_power_base"]
    base_armor = (dex_val * 0.05) + (level * 0.2) + class_mods["armor_base"]

    base_rates = RestorationRates(
        health_per_second=base_health,
        stamina_per_second=base_stamina,
        tech_power_per_second=base_tech_power,
        armor_per_second=base_armor,
    )

    # Get equipment and buff modifiers
    equipment_mods = calculate_equipment_restoration_modifiers(character)
    buff_mods = calculate_buff_restoration_modifiers(character)

    # Apply modifiers
    return apply_restoration_modifiers(base_rates, equipment_mods, buff_mods)


def restore_resources(character: "Character | NPC", elapsed_seconds: float) -> RestorationResult:
    """
    Apply restoration over elapsed time.

    Args:
        character: Character or NPC to restore
        elapsed_seconds: Number of seconds elapsed

    Returns:
        RestorationResult with amounts restored
    """
    if character.is_incapacitated:
        # Don't restore if incapacitated
        return RestorationResult(
            character=character,
            elapsed_seconds=elapsed_seconds,
        )

    # Calculate restoration rates
    rates = calculate_restoration_rates(character)

    # Calculate amounts to restore
    health_to_restore = rates.health_per_second * elapsed_seconds
    stamina_to_restore = rates.stamina_per_second * elapsed_seconds
    tech_power_to_restore = rates.tech_power_per_second * elapsed_seconds
    armor_to_restore = rates.armor_per_second * elapsed_seconds

    # Store before values
    before_health = character.current_health
    before_stamina = character.current_stamina
    before_tech_power = character.current_tech_power
    before_armor = character.current_armor

    # Apply restoration (cap at max)
    character.current_health = min(
        character.max_health, character.current_health + health_to_restore
    )
    character.current_stamina = min(
        character.max_stamina, character.current_stamina + stamina_to_restore
    )
    character.current_tech_power = min(
        character.max_tech_power, character.current_tech_power + tech_power_to_restore
    )
    character.current_armor = min(character.max_armor, character.current_armor + armor_to_restore)

    # Calculate actual amounts restored
    health_restored = character.current_health - before_health
    stamina_restored = character.current_stamina - before_stamina
    tech_power_restored = character.current_tech_power - before_tech_power
    armor_restored = character.current_armor - before_armor

    return RestorationResult(
        character=character,
        health_restored=health_restored,
        stamina_restored=stamina_restored,
        tech_power_restored=tech_power_restored,
        armor_restored=armor_restored,
        elapsed_seconds=elapsed_seconds,
    )


def catch_up_restoration(
    character: "Character | NPC", last_update_time: datetime
) -> RestorationResult:
    """
    Calculate and apply restoration for time away.

    Args:
        character: Character or NPC to restore
        last_update_time: Timestamp of last resource update

    Returns:
        RestorationResult with amounts restored
    """
    now = datetime.now(UTC)
    elapsed_seconds = (now - last_update_time).total_seconds()

    if elapsed_seconds <= 0:
        return RestorationResult(
            character=character,
            elapsed_seconds=0.0,
        )

    return restore_resources(character, elapsed_seconds)
