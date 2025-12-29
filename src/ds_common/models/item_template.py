from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON
from sqlmodel import Column, Field, Relationship

from ds_common.models.base_model import BaseSQLModel
from ds_common.models.junction_tables import CharacterClassStartingEquipment

if TYPE_CHECKING:
    from ds_common.models.character_class import CharacterClass
    from ds_common.models.item_category import ItemCategory


class ItemTemplate(BaseSQLModel, table=True):
    """
    Item template model - reusable item definitions
    """

    __tablename__ = "item_templates"

    name: str = Field(unique=True, index=True, description="Item template name")
    description: str = Field(description="Item template description")
    category_id: UUID = Field(foreign_key="item_categories.id", description="Item category")
    equippable_slots: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="List of equipment slots this item can be equipped to",
    )
    rarity: str = Field(
        default="common",
        description="Item rarity: common, uncommon, rare, epic, legendary",
    )
    value: int = Field(default=0, description="Item value in credits")

    # Effect properties (JSON dicts)
    stat_bonuses: dict[str, float] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Stat bonuses (e.g., {'STR': 5.0, 'DEX': 2.0})",
    )
    stat_multipliers: dict[str, float] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Stat multipliers (e.g., {'INT': 1.2})",
    )
    resource_bonuses: dict[str, float] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Max resource bonuses (e.g., {'max_health': 20.0, 'max_stamina': 10.0})",
    )
    resource_regeneration_modifiers: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Resource regeneration modifiers (e.g., {'health': {'bonus': 0.5, 'multiplier': 1.2}})",
    )
    damage_bonuses: dict[str, float] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Damage type bonuses (e.g., {'physical': 10.0, 'tech': 5.0})",
    )
    damage_multipliers: dict[str, float] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Damage type multipliers (e.g., {'physical': 1.15})",
    )
    healing_bonuses: dict[str, float] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Healing bonuses (e.g., {'heal_amount': 5.0})",
    )
    inventory_slots_bonus: int = Field(
        default=0,
        description="Additional inventory slots provided by this item",
    )

    # Relationships
    category: "ItemCategory" = Relationship(back_populates="item_templates")
    starting_equipment_for_classes: list["CharacterClass"] = Relationship(
        back_populates="starting_equipment",
        link_model=CharacterClassStartingEquipment,
    )
