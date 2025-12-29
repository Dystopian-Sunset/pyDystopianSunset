"""
Location edge model for graph-based location system.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, Relationship

from ds_common.models.base_model import BaseSQLModel

if TYPE_CHECKING:
    from ds_common.models.location_node import LocationNode


class LocationEdge(BaseSQLModel, table=True):
    """
    Location edge model for graph-based location system.

    Represents a connection/route between two locations in the world graph.
    """

    __tablename__ = "location_edges"
    __table_args__ = (
        UniqueConstraint(
            "from_location_id", "to_location_id", "edge_type", name="uq_location_edge"
        ),
    )

    from_location_id: UUID = Field(
        foreign_key="location_nodes.id", description="Source location node ID"
    )
    to_location_id: UUID = Field(
        foreign_key="location_nodes.id", description="Destination location node ID"
    )
    edge_type: str = Field(description="Edge type: DIRECT, REQUIRES_TRAVEL, SECRET, CONDITIONAL")
    travel_method: str | None = Field(
        default=None, max_length=100, description="Travel method: walk, transport, vehicle, etc."
    )
    travel_time: str | None = Field(
        default=None, max_length=100, description="Travel time: minutes, hours, etc."
    )
    requirements: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Travel requirements: {credits: int, items: [], permissions: []}",
    )
    narrative_description: str | None = Field(
        default=None, description="Narrative description of the route"
    )
    conditions: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Route conditions: {time_of_day: str, weather: str, etc.}",
    )
    discovered_by: UUID | None = Field(
        default=None, foreign_key="characters.id", description="Character who discovered this route"
    )
    discovered_at: datetime | None = Field(
        default=None, description="When this route was discovered (UTC)"
    )
    discovered_in_session: UUID | None = Field(
        default=None,
        foreign_key="game_sessions.id",
        description="Game session where this route was discovered",
    )

    # Relationships
    from_location: "LocationNode" = Relationship(
        back_populates="outgoing_edges",
        sa_relationship_kwargs={
            "foreign_keys": "[LocationEdge.from_location_id]",
        },
    )
    to_location: "LocationNode" = Relationship(
        back_populates="incoming_edges",
        sa_relationship_kwargs={
            "foreign_keys": "[LocationEdge.to_location_id]",
        },
    )
