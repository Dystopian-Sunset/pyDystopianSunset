from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from ds_common.models.base_model import BaseSQLModel

if TYPE_CHECKING:
    from ds_common.models.item_template import ItemTemplate


class ItemCategory(BaseSQLModel, table=True):
    """
    Item category model (weapon, armor, implant, etc.)
    """

    __tablename__ = "item_categories"

    name: str = Field(unique=True, index=True, description="Category name")
    description: str = Field(description="Category description")
    emoji: str = Field(description="Category emoji")

    # Relationships
    item_templates: list["ItemTemplate"] = Relationship(back_populates="category")
