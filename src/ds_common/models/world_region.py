from typing import Literal
from uuid import UUID

from sqlalchemy import ARRAY, JSON, Column, String
from sqlalchemy.dialects import postgresql
from sqlmodel import Field

from ds_common.models.base_model import BaseSQLModel

# Type alias for type checking (not used in SQLModel fields)
RegionType = Literal["CITY", "DISTRICT", "SECTOR", "FACTION_TERRITORY", "CUSTOM"]


class WorldRegion(BaseSQLModel, table=True):
    """
    World region model for hierarchical regions (City -> District -> Sector).

    Supports faction territories and regional variations.
    """

    __tablename__ = "world_regions"

    name: str = Field(max_length=255, description="Region name")
    region_type: str = Field(
        description="Type of region"
    )  # RegionType = Literal["CITY", "DISTRICT", "SECTOR", "FACTION_TERRITORY", "CUSTOM"]
    description: str | None = Field(default=None, description="Region description")

    # Hierarchy
    parent_region_id: UUID | None = Field(
        default=None, foreign_key="world_regions.id", description="Parent region ID"
    )
    hierarchy_level: int = Field(
        default=0, description="Hierarchy level (0=city, 1=district, 2=sector)"
    )

    # Location associations
    city: str | None = Field(default=None, description="City name if applicable")
    locations: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String)),
        description="Location strings associated with this region",
    )

    # Faction associations
    factions: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String)),
        description="Factions that control or are associated with this region",
    )

    # Custom boundaries
    custom_boundaries: dict | None = Field(
        default=None, sa_column=Column(JSON), description="Custom boundary definitions"
    )

    # Active elements
    active_events: list[UUID] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(postgresql.UUID(as_uuid=True))),
        description="Active world event IDs in this region",
    )

    # Regional variations
    regional_variations: dict | None = Field(
        default=None, sa_column=Column(JSON), description="Regional variations and properties"
    )
