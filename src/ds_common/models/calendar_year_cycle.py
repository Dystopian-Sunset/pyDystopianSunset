"""
Calendar year cycle model for tracking the 12-year cycle similar to Chinese calendar.
"""

from sqlalchemy import ARRAY, Column, String
from sqlmodel import Field

from ds_common.models.base_model import BaseSQLModel


class CalendarYearCycle(BaseSQLModel, table=True):
    """
    Calendar year cycle model for storing the 12-year cycle with animal associations.

    Each year in the cycle (1-12) is associated with an animal.
    """

    __tablename__ = "calendar_year_cycles"

    cycle_year: int = Field(
        unique=True,
        index=True,
        description="Year in the cycle (1-12)",
    )
    animal_name: str = Field(
        max_length=255,
        description="Animal associated with this year",
    )
    animal_description: str | None = Field(
        default=None,
        description="Description of the animal and its significance",
    )
    traits: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String)),
        description="Traits associated with this year/animal",
    )
    cultural_significance: str | None = Field(
        default=None,
        description="Cultural significance and history of this animal in the cycle",
    )
