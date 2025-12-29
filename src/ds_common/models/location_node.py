"""
Location node model for graph-based location system.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship

from ds_common.models.base_model import BaseSQLModel

if TYPE_CHECKING:
    from ds_common.models.location_edge import LocationEdge
    from ds_common.models.location_fact import LocationFact


class LocationNode(BaseSQLModel, table=True):
    """
    Location node model for graph-based location system.

    Represents a location in the world graph (cities, districts, sectors, POIs).
    """

    __tablename__ = "location_nodes"

    location_name: str = Field(unique=True, index=True, max_length=255, description="Location name")
    location_type: str = Field(description="Location type: CITY, DISTRICT, SECTOR, POI, CUSTOM")
    description: str | None = Field(default=None, description="Rich narrative description")
    atmosphere: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Sensory details: {sights: [], sounds: [], smells: []}",
    )
    physical_properties: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Physical properties: {distance: str, elevation: str, accessibility: str}",
    )
    theme: str | None = Field(
        default=None, max_length=100, description="Theme: cyberpunk, industrial, residential, etc."
    )
    character_associations: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Character associations: {nearby_npcs: [], factions: [], npc_relationships: []}",
    )
    location_fact_id: UUID | None = Field(
        default=None, foreign_key="location_facts.id", description="Related LocationFact ID"
    )
    parent_location_id: UUID | None = Field(
        default=None,
        foreign_key="location_nodes.id",
        description="Parent location node ID (for POIs within cities)",
    )
    discovered_by: UUID | None = Field(
        default=None,
        foreign_key="characters.id",
        description="Character who discovered this location",
    )
    discovered_at: datetime | None = Field(
        default=None, description="When this location was discovered (UTC)"
    )
    discovered_in_session: UUID | None = Field(
        default=None,
        foreign_key="game_sessions.id",
        description="Game session where this location was discovered",
    )

    # Relationships
    location_fact: "LocationFact" = Relationship()
    parent_location: "LocationNode" = Relationship(
        back_populates="child_locations",
        sa_relationship_kwargs={
            "foreign_keys": "[LocationNode.parent_location_id]",
            "remote_side": "[LocationNode.id]",
        },
    )
    child_locations: list["LocationNode"] = Relationship(
        back_populates="parent_location",
        sa_relationship_kwargs={
            "foreign_keys": "[LocationNode.parent_location_id]",
        },
    )
    outgoing_edges: list["LocationEdge"] = Relationship(
        back_populates="from_location",
        sa_relationship_kwargs={
            "foreign_keys": "[LocationEdge.from_location_id]",
        },
    )
    incoming_edges: list["LocationEdge"] = Relationship(
        back_populates="to_location",
        sa_relationship_kwargs={
            "foreign_keys": "[LocationEdge.to_location_id]",
        },
    )
