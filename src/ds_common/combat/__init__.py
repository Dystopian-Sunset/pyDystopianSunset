"""
Combat system module for handling combat resources, damage, and restoration.
"""

from ds_common.combat.damage_handler import (
    apply_damage,
    apply_healing,
    check_incapacitation,
    consume_stamina,
    consume_tech_power,
    restore_stamina,
    restore_tech_power,
    update_armor,
)
from ds_common.combat.display import format_combat_status, format_resource_display
from ds_common.combat.models import (
    CombatResult,
    CombatStatus,
    DamageType,
    RestorationModifiers,
    RestorationRates,
    RestorationResult,
)
from ds_common.combat.resource_calculator import (
    calculate_max_armor,
    calculate_max_health,
    calculate_max_stamina,
    calculate_max_tech_power,
)
from ds_common.combat.restoration_service import (
    calculate_buff_restoration_modifiers,
    calculate_equipment_restoration_modifiers,
    calculate_restoration_rates,
    catch_up_restoration,
    restore_resources,
)

__all__ = [
    "CombatResult",
    "CombatStatus",
    "DamageType",
    "RestorationModifiers",
    "RestorationRates",
    "RestorationResult",
    "apply_damage",
    "apply_healing",
    "calculate_buff_restoration_modifiers",
    "calculate_equipment_restoration_modifiers",
    "calculate_max_armor",
    "calculate_max_health",
    "calculate_max_stamina",
    "calculate_max_tech_power",
    "calculate_restoration_rates",
    "catch_up_restoration",
    "check_incapacitation",
    "consume_stamina",
    "consume_tech_power",
    "format_combat_status",
    "format_resource_display",
    "restore_resources",
    "restore_stamina",
    "restore_tech_power",
    "update_armor",
]
