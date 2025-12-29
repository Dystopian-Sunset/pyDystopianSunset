from typing import TYPE_CHECKING

from sqlalchemy import JSON
from sqlmodel import Column, Field, Relationship

from ds_common.models.base_model import BaseSQLModel
from ds_common.models.junction_tables import CharacterQuest

if TYPE_CHECKING:
    from ds_common.models.character import Character


class Quest(BaseSQLModel, table=True):
    """
    Quest model
    """

    __tablename__ = "quests"

    name: str = Field(description="Quest name")
    description: str = Field(description="Quest description")
    tasks: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="Quest tasks",
    )

    # Relationships
    characters: list["Character"] = Relationship(
        back_populates="quests",
        link_model=CharacterQuest,
    )
