from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from ds_common.models.base_model import BaseSQLModel
from ds_common.models.junction_tables import (
    CharacterClassStartingEquipment,
    CharacterClassStat,
)

if TYPE_CHECKING:
    from ds_common.models.character import Character
    from ds_common.models.character_stat import CharacterStat
    from ds_common.models.item_template import ItemTemplate


class CharacterClass(BaseSQLModel, table=True):
    """
    Character class model
    """

    __tablename__ = "character_classes"

    name: str = Field(description="Character class name")
    description: str = Field(description="Character class description")
    emoji: str = Field(description="Character class emoji")

    # Relationships
    characters: list["Character"] = Relationship(back_populates="character_class")
    stats: list["CharacterStat"] = Relationship(
        back_populates="character_classes",
        link_model=CharacterClassStat,
    )
    starting_equipment: list["ItemTemplate"] = Relationship(
        back_populates="starting_equipment_for_classes",
        link_model=CharacterClassStartingEquipment,
    )
