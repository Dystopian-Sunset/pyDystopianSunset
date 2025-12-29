from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import ARRAY, JSON, Column, DateTime
from sqlalchemy.dialects import postgresql
from sqlmodel import Field

from ds_common.models.base_model import BaseSQLModel

# Type aliases for type checking (not used in SQLModel fields)
ItemType = Literal["UNIQUE", "QUEST_GOAL", "COLLECTIBLE", "ARTIFACT", "FACTION_RELIC"]
ItemStatus = Literal["AVAILABLE", "COLLECTED", "DESTROYED", "HIDDEN"]


class WorldItem(BaseSQLModel, table=True):
    """
    World item model for unique collectible items in the world.

    Supports "first come, first served" mechanics and quest integration.
    """

    __tablename__ = "world_items"

    name: str = Field(max_length=255, description="Item name")
    description: str | None = Field(default=None, description="Item description")
    item_type: str = Field(
        description="Type of world item"
    )  # ItemType = Literal["UNIQUE", "QUEST_GOAL", "COLLECTIBLE", "ARTIFACT", "FACTION_RELIC"]
    status: str = Field(
        default="AVAILABLE", description="Current item status"
    )  # ItemStatus = Literal["AVAILABLE", "COLLECTED", "DESTROYED", "HIDDEN"]

    # Collection
    collection_condition: dict | None = Field(
        default=None, sa_column=Column(JSON), description="Conditions for collection"
    )
    collected_by: UUID | None = Field(
        default=None, foreign_key="characters.id", description="Character who collected it"
    )
    collected_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        description="Real time when collected (UTC)",
    )
    collected_at_game_time: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Game time when collected: {year, day, hour}",
    )
    collection_session_id: UUID | None = Field(
        default=None, foreign_key="game_sessions.id", description="Session when collected"
    )

    # Quest integration
    quest_goals: list[UUID] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(postgresql.UUID(as_uuid=True))),
        description="Quest IDs that require this item",
    )

    # Location and availability
    location_hint: str | None = Field(default=None, description="Hint about item location")
    regional_availability: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Regional availability: {regions: [], locations: []}",
    )
    faction_origin: str | None = Field(
        default=None, description="Faction that originally owned/created this item"
    )

    # Related entities
    related_world_memories: list[UUID] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(postgresql.UUID(as_uuid=True))),
        description="World memory IDs related to this item",
    )
