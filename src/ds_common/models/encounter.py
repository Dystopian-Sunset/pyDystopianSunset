from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship

from ds_common.models.base_model import BaseSQLModel
from ds_common.models.junction_tables import EncounterCharacter, EncounterNPC

if TYPE_CHECKING:
    from ds_common.models.character import Character
    from ds_common.models.game_session import GameSession
    from ds_common.models.npc import NPC


class EncounterType(str, Enum):
    """Encounter type enumeration"""

    COMBAT = "combat"
    SOCIAL = "social"
    ENVIRONMENTAL_HAZARD = "environmental_hazard"


class EncounterStatus(str, Enum):
    """Encounter status enumeration"""

    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class Encounter(BaseSQLModel, table=True):
    """
    Encounter model for tracking active encounters in game sessions
    """

    __tablename__ = "encounters"

    game_session_id: UUID = Field(
        foreign_key="game_sessions.id", index=True, description="Game session ID"
    )
    encounter_type: EncounterType = Field(description="Type of encounter")
    status: EncounterStatus = Field(default=EncounterStatus.ACTIVE, description="Encounter status")
    description: str | None = Field(default=None, description="Encounter description")

    # Reward tracking
    dead_npcs: list[UUID] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="List of NPC IDs that died in this encounter",
    )
    rewards_distributed: bool = Field(
        default=False,
        description="Whether experience rewards have been distributed",
    )
    searched_npcs: list[UUID] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="List of NPC IDs that have been searched for loot",
    )

    # Relationships
    game_session: "GameSession" = Relationship()
    characters: list["Character"] = Relationship(
        back_populates="encounters",
        link_model=EncounterCharacter,
    )
    npcs: list["NPC"] = Relationship(
        back_populates="encounters",
        link_model=EncounterNPC,
    )
