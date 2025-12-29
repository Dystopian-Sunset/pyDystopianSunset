import random
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime
from sqlmodel import Column, Field, Relationship

from ds_common.combat import (
    calculate_max_armor,
    calculate_max_health,
    calculate_max_stamina,
    calculate_max_tech_power,
)
from ds_common.models.base_model import BaseSQLModel
from ds_common.models.junction_tables import EncounterNPC

if TYPE_CHECKING:
    from ds_common.models.encounter import Encounter


class NPC(BaseSQLModel, table=True):
    """
    NPC (Non-Player Character) model
    """

    __tablename__ = "npcs"

    name: str = Field(description="NPC name")
    race: str = Field(description="NPC race")
    background: str = Field(description="NPC background")
    profession: str = Field(description="NPC profession")
    faction: str | None = Field(default=None, description="NPC faction")
    location: str | None = Field(default=None, description="NPC location")
    level: int = Field(description="NPC level")
    credits: int = Field(description="NPC credits")
    stats: dict[str, int] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="NPC stats",
    )
    effects: dict[str, int] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="NPC effects",
    )
    renown: int = Field(description="NPC renown")
    shadow_level: int = Field(description="NPC shadow level")
    last_active: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        description="NPC last active timestamp (UTC)",
    )

    # Combat resources
    current_health: float = Field(default=0.0, description="Current health points")
    max_health: float = Field(default=0.0, description="Maximum health points")
    current_stamina: float = Field(default=0.0, description="Current stamina points")
    max_stamina: float = Field(default=0.0, description="Maximum stamina points")
    current_tech_power: float = Field(default=0.0, description="Current tech power/mana")
    max_tech_power: float = Field(default=0.0, description="Maximum tech power/mana")
    current_armor: float = Field(default=0.0, description="Current armor/shield points")
    max_armor: float = Field(default=0.0, description="Maximum armor/shield points")
    is_incapacitated: bool = Field(default=False, description="Whether NPC is incapacitated")
    last_resource_update: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="Timestamp of last resource restoration (UTC)",
    )

    # Relationships
    encounters: list["Encounter"] = Relationship(
        back_populates="npcs",
        link_model=EncounterNPC,
    )

    @classmethod
    async def generate_npc(
        cls,
        name: str,
        race: str,
        background: str,
        profession: str,
        faction: str | None,
        location: str | None,
    ) -> "NPC":
        level = random.randint(1, 100)
        credits = random.randint(1, 100) * level

        max_total_stats = 100 * (level * 1.2)

        stats = {}
        # Generate stats, with a maximum of max_stats
        for stat in ["CHA", "DEX", "INT", "LUK", "PER", "STR"]:
            max_stat_value = int(max_total_stats / 6)
            stat_value = random.randint(1, max_stat_value if max_stat_value > 0 else 1)
            max_total_stats -= stat_value

            stats[stat] = stat_value

        npc = cls(
            name=name,
            race=race,
            background=background,
            profession=profession,
            faction=faction,
            location=location,
            level=level,
            credits=credits,
            stats=stats,
            effects={},
            renown=0,
            shadow_level=0,
            created_at=datetime.now(UTC),
            last_active=datetime.now(UTC),
        )

        # Initialize combat resources (NPCs don't have character classes)
        npc.max_health = calculate_max_health(npc, None)
        npc.max_stamina = calculate_max_stamina(npc, None)
        npc.max_tech_power = calculate_max_tech_power(npc, None)
        npc.max_armor = calculate_max_armor(npc, None)

        # Set current resources to max
        npc.current_health = npc.max_health
        npc.current_stamina = npc.max_stamina
        npc.current_tech_power = npc.max_tech_power
        npc.current_armor = npc.max_armor

        # Set last_resource_update
        npc.last_resource_update = datetime.now(UTC)

        return npc
