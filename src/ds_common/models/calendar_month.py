"""
Calendar month model for tracking months of the year with names and history.
"""

from sqlalchemy import JSON, Column, Integer
from sqlmodel import Field

from ds_common.models.base_model import BaseSQLModel


class CalendarMonth(BaseSQLModel, table=True):
    """
    Calendar month model for storing month names and historical information.

    The calendar has 20 months totaling 400 days. Four peak months (27 days each)
    are centered on season peaks (days 50, 150, 250, 350), with 16 regular months
    (18-19 days each) filling the gaps.
    """

    __tablename__ = "calendar_months"

    month_number: int = Field(
        sa_column=Column(Integer, unique=True, index=True),
        description="Month number (1-20)",
    )
    name: str = Field(
        max_length=255,
        description="Month name",
    )
    short_name: str | None = Field(
        default=None,
        max_length=50,
        description="Short/abbreviated month name",
    )
    days: int = Field(
        default=18,
        description="Number of days in this month (18-19 for regular months, 27 for peak months)",
    )
    season: str | None = Field(
        default=None,
        description="Primary season for this month (SPRING, SUMMER, FALL, WINTER)",
    )
    description: str | None = Field(
        default=None,
        description="Description of the month",
    )
    history: str | None = Field(
        default=None,
        description="Historical context and origin of the month name",
    )
    cultural_significance: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Cultural significance: {factions: [], traditions: [], events: []}",
    )
    regional_variations: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Regional variations in month name or celebration",
    )
