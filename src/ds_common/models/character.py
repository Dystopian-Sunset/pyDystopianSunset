import random
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import JSON, DateTime
from sqlmodel import Column, Field, Relationship

from ds_common.models.base_model import BaseSQLModel
from ds_common.models.junction_tables import (
    CharacterQuest,
    EncounterCharacter,
    GameSessionCharacter,
    PlayerCharacter,
)

if TYPE_CHECKING:
    from ds_common.models.character_class import CharacterClass
    from ds_common.models.character_cooldown import CharacterCooldown
    from ds_common.models.encounter import Encounter
    from ds_common.models.game_session import GameSession
    from ds_common.models.player import Player
    from ds_common.models.quest import Quest


class Character(BaseSQLModel, table=True):
    """
    Player character model
    """

    __tablename__ = "characters"

    name: str = Field(unique=True, index=True, description="Character name")
    gender: str | None = Field(
        default=None,
        description="Character gender: 'Female', 'Male', 'Other', or None",
    )
    level: int = Field(default=1, description="Character level")
    exp: int = Field(default=0, description="Character experience")
    credits: int = Field(default=0, description="Character monetary credits")
    stats: dict[str, int] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Character stats",
    )
    effects: dict[str, int] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Effects are temporary modifiers to stats",
    )
    inventory: list[dict] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="Character inventory items",
    )
    equipped_items: dict[str, str | None] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Maps equipment slot names to item instance IDs",
    )
    renown: int = Field(default=0, description="Character renown")
    shadow_level: int = Field(default=0, description="Character shadow level")

    # Combat resources
    current_health: float = Field(default=0.0, description="Current health points")
    max_health: float = Field(default=0.0, description="Maximum health points")
    current_stamina: float = Field(default=0.0, description="Current stamina points")
    max_stamina: float = Field(default=0.0, description="Maximum stamina points")
    current_tech_power: float = Field(default=0.0, description="Current tech power/mana")
    max_tech_power: float = Field(default=0.0, description="Maximum tech power/mana")
    current_armor: float = Field(default=0.0, description="Current armor/shield points")
    max_armor: float = Field(default=0.0, description="Maximum armor/shield points")
    is_incapacitated: bool = Field(default=False, description="Whether character is incapacitated")
    last_resource_update: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="Timestamp of last resource restoration (UTC)",
    )

    # Foreign keys
    character_class_id: UUID | None = Field(default=None, foreign_key="character_classes.id")
    current_location: UUID | None = Field(
        default=None,
        foreign_key="location_nodes.id",
        description="Current location node ID",
    )

    # Relationships
    players: list["Player"] = Relationship(
        back_populates="characters",
        link_model=PlayerCharacter,
    )
    active_for_player: Optional["Player"] = Relationship(
        back_populates="active_character",
        sa_relationship_kwargs={
            "foreign_keys": "[Player.active_character_id]",
            "primaryjoin": "Player.active_character_id == Character.id",
        },
    )
    character_class: Optional["CharacterClass"] = Relationship()
    game_sessions: list["GameSession"] = Relationship(
        back_populates="characters",
        link_model=GameSessionCharacter,
    )
    quests: list["Quest"] = Relationship(
        back_populates="characters",
        link_model=CharacterQuest,
    )
    encounters: list["Encounter"] = Relationship(
        back_populates="characters",
        link_model=EncounterCharacter,
    )
    cooldowns: list["CharacterCooldown"] = Relationship(back_populates="character")

    def get_exp_for_next_level(self) -> int:
        """
        Get the total experience required to reach the next level.

        Returns:
            Total experience required for next level
        """
        from ds_common.combat.experience_service import calculate_exp_for_level

        return calculate_exp_for_level(self.level + 1)

    @classmethod
    def generate_character(
        cls,
        name: str,
    ) -> "Character":
        return cls(
            name=name,
            level=1,
            exp=0,
            credits=100,
            stats={
                "CHA": random.randint(1, 20),
                "DEX": random.randint(1, 20),
                "INT": random.randint(1, 20),
                "LUK": random.randint(1, 20),
                "PER": random.randint(1, 20),
                "STR": random.randint(1, 20),
            },
            effects={},
            renown=0,
            shadow_level=0,
            created_at=datetime.now(UTC),
            last_active_at=datetime.now(UTC),
        )
