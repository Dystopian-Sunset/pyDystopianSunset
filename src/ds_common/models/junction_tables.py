"""
Junction tables for many-to-many relationships.

These tables replace SurrealDB graph relationships with relational many-to-many tables.
"""

from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class PlayerCharacter(SQLModel, table=True):
    """
    Junction table for player-character relationship.
    Replaces SurrealDB: player_has_character
    """

    __tablename__ = "player_characters"

    player_id: UUID = Field(primary_key=True, foreign_key="players.id")
    character_id: UUID = Field(primary_key=True, foreign_key="characters.id")


class GameSessionPlayer(SQLModel, table=True):
    """
    Junction table for game session-player relationship.
    Replaces SurrealDB: player_is_playing_in
    """

    __tablename__ = "game_session_players"

    game_session_id: UUID = Field(primary_key=True, foreign_key="game_sessions.id")
    player_id: UUID = Field(primary_key=True, foreign_key="players.id")


class GameSessionCharacter(SQLModel, table=True):
    """
    Junction table for game session-character relationship.
    Replaces SurrealDB: character_is_playing_in
    """

    __tablename__ = "game_session_characters"

    game_session_id: UUID = Field(primary_key=True, foreign_key="game_sessions.id")
    character_id: UUID = Field(primary_key=True, foreign_key="characters.id")


class CharacterClassStat(SQLModel, table=True):
    """
    Junction table for character class-stat relationship.
    Replaces SurrealDB: has_class_stat
    """

    __tablename__ = "character_class_stats"

    character_class_id: UUID = Field(primary_key=True, foreign_key="character_classes.id")
    character_stat_id: UUID = Field(primary_key=True, foreign_key="character_stats.id")


class CharacterQuest(SQLModel, table=True):
    """
    Junction table for character-quest relationship.
    Replaces SurrealDB: has_quest

    Tracks items given to the character when accepting the quest.
    These items will be removed if the quest is abandoned or the session ends.
    """

    __tablename__ = "character_quests"

    character_id: UUID = Field(primary_key=True, foreign_key="characters.id")
    quest_id: UUID = Field(primary_key=True, foreign_key="quests.id")
    items_given: list[dict] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="Items given to character when accepting this quest. Format: [{'name': 'Item Name', 'quantity': 1, 'instance_id': '...'}]",
    )
    session_id: UUID | None = Field(
        default=None,
        foreign_key="game_sessions.id",
        description="Session ID when quest was accepted. Used for cleanup when session ends.",
    )


class EncounterCharacter(SQLModel, table=True):
    """
    Junction table for encounter-character relationship.
    """

    __tablename__ = "encounter_characters"

    encounter_id: UUID = Field(primary_key=True, foreign_key="encounters.id")
    character_id: UUID = Field(primary_key=True, foreign_key="characters.id")


class EncounterNPC(SQLModel, table=True):
    """
    Junction table for encounter-NPC relationship.
    """

    __tablename__ = "encounter_npcs"

    encounter_id: UUID = Field(primary_key=True, foreign_key="encounters.id")
    npc_id: UUID = Field(primary_key=True, foreign_key="npcs.id")


class CharacterClassStartingEquipment(SQLModel, table=True):
    """
    Junction table for character class starting equipment.
    Links character classes to their starting item templates.
    """

    __tablename__ = "character_class_starting_equipment"

    character_class_id: UUID = Field(primary_key=True, foreign_key="character_classes.id")
    item_template_id: UUID = Field(primary_key=True, foreign_key="item_templates.id")
    equipment_slot: str = Field(description="Slot to auto-equip this item to")
    quantity: int = Field(default=1, description="Quantity of this item to give")
