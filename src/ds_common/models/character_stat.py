from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from ds_common.models.base_model import BaseSQLModel
from ds_common.models.junction_tables import CharacterClassStat

if TYPE_CHECKING:
    from ds_common.models.character_class import CharacterClass


class CharacterStat(BaseSQLModel, table=True):
    """
    Character stat model
    """

    __tablename__ = "character_stats"

    name: str = Field(description="Character stat name")
    abbr: str = Field(description="Character stat abbreviation")
    description: str = Field(description="Character stat description")
    emoji: str = Field(description="Character stat emoji")
    max_value: int = Field(description="Character stat maximum value")
    is_primary: bool = Field(description="Character stat is primary")
    is_mutable: bool = Field(description="Character stat is mutable")

    # Relationships
    character_classes: list["CharacterClass"] = Relationship(
        back_populates="stats",
        link_model=CharacterClassStat,
    )
