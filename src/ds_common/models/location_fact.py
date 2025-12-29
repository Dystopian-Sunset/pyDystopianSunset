"""
Location fact model for storing geography facts, travel requirements, and location relationships.
"""

from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field

from ds_common.models.base_model import BaseSQLModel


class LocationFact(BaseSQLModel, table=True):
    """
    Location fact model for storing geography facts and travel requirements.

    Stores facts about locations, their relationships, and travel constraints.
    """

    __tablename__ = "location_facts"

    location_name: str = Field(
        index=True, max_length=255, description="Location name (city, district, sector, etc.)"
    )
    location_type: str = Field(description="Location type: CITY, DISTRICT, SECTOR, or CUSTOM")

    # Facts about the location
    facts: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="List of established facts about this location",
    )

    # Geography relationships
    connections: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Location connections: {direct: [], requires_travel: [], not_connected: []}",
    )

    # Travel requirements
    travel_requirements: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Travel requirements: {from_location: {method: str, time: str, requirements: []}}",
    )

    # Physical properties
    physical_properties: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Physical properties: {distance: str, accessibility: str, elevation: str, etc.}",
    )

    # Related region (optional foreign key)
    region_id: UUID | None = Field(
        default=None, foreign_key="world_regions.id", description="Related WorldRegion ID"
    )

    # Constraints
    constraints: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Constraints: {cannot_reach_by: [], requires: [], forbidden_actions: []}",
    )
