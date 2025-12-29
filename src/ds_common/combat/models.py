"""
Combat system models and data structures.
"""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ds_common.models.character import Character
    from ds_common.models.npc import NPC


class DamageType(str, Enum):
    """Damage type enumeration"""

    PHYSICAL = "physical"
    TECH = "tech"
    ENVIRONMENTAL = "environmental"


class CombatStatus(str, Enum):
    """Combat status enumeration"""

    ACTIVE = "active"
    INCAPACITATED = "incapacitated"
    UNCONSCIOUS = "unconscious"


@dataclass
class CombatResult:
    """Result of a combat action"""

    character: "Character | NPC"
    before_health: float
    after_health: float
    before_stamina: float | None = None
    after_stamina: float | None = None
    before_tech_power: float | None = None
    after_tech_power: float | None = None
    before_armor: float | None = None
    after_armor: float | None = None
    message: str | None = None
    is_incapacitated: bool = False


@dataclass
class RestorationModifiers:
    """Equipment and buff modifiers for restoration rates"""

    health_bonus: float = 0.0
    health_multiplier: float = 1.0
    stamina_bonus: float = 0.0
    stamina_multiplier: float = 1.0
    tech_power_bonus: float = 0.0
    tech_power_multiplier: float = 1.0
    armor_bonus: float = 0.0
    armor_multiplier: float = 1.0


@dataclass
class RestorationRates:
    """Per-second restoration rates for each resource"""

    health_per_second: float = 0.0
    stamina_per_second: float = 0.0
    tech_power_per_second: float = 0.0
    armor_per_second: float = 0.0


@dataclass
class RestorationResult:
    """Result of resource restoration"""

    character: "Character | NPC"
    health_restored: float = 0.0
    stamina_restored: float = 0.0
    tech_power_restored: float = 0.0
    armor_restored: float = 0.0
    elapsed_seconds: float = 0.0
