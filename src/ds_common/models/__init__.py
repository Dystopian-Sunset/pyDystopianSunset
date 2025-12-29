"""
Models package - imports all models to ensure they are registered with SQLModel metadata.

This ensures all models are available when SQLAlchemy tries to resolve relationships.
Import order matters - base models and junction tables should be imported before models that use them.
"""

# Import base model first
from ds_common.models.base_model import BaseSQLModel  # noqa: F401
from ds_common.models.calendar_event import CalendarEvent  # noqa: F401
from ds_common.models.calendar_month import CalendarMonth  # noqa: F401
from ds_common.models.calendar_year_cycle import CalendarYearCycle  # noqa: F401

# Import other models
from ds_common.models.character import Character  # noqa: F401
from ds_common.models.character_class import CharacterClass  # noqa: F401

# Import CharacterCooldown after Character (CharacterCooldown has FK to Character)
from ds_common.models.character_cooldown import CharacterCooldown  # noqa: F401
from ds_common.models.character_recognition import CharacterRecognition  # noqa: F401
from ds_common.models.character_stat import CharacterStat  # noqa: F401
from ds_common.models.encounter import Encounter  # noqa: F401
from ds_common.models.episode_memory import EpisodeMemory  # noqa: F401
from ds_common.models.game_history_embedding import GameHistoryEmbedding  # noqa: F401
from ds_common.models.game_master import GMHistory  # noqa: F401
from ds_common.models.game_session import GameSession  # noqa: F401
from ds_common.models.game_settings import GameSettings  # noqa: F401
from ds_common.models.game_time import GameTime  # noqa: F401

# Import item models before character_class (since CharacterClass has relationship to ItemTemplate)
from ds_common.models.item_category import ItemCategory  # noqa: F401
from ds_common.models.item_template import ItemTemplate  # noqa: F401

# Import junction tables (they reference models, so models should be imported first)
from ds_common.models.junction_tables import (  # noqa: F401
    CharacterClassStartingEquipment,
    CharacterClassStat,
    CharacterQuest,
    EncounterCharacter,
    EncounterNPC,
    GameSessionCharacter,
    GameSessionPlayer,
    PlayerCharacter,
)
from ds_common.models.location_edge import LocationEdge  # noqa: F401

# Import location graph models before Character (Character has FK to LocationNode)
# Import LocationFact before LocationNode (LocationNode has FK to LocationFact)
from ds_common.models.location_fact import LocationFact  # noqa: F401
from ds_common.models.location_node import LocationNode  # noqa: F401
from ds_common.models.memory_settings import MemorySettings  # noqa: F401
from ds_common.models.memory_snapshot import MemorySnapshot  # noqa: F401
from ds_common.models.npc import NPC  # noqa: F401
from ds_common.models.npc_memory import NPCMemory  # noqa: F401
from ds_common.models.player import Player  # noqa: F401
from ds_common.models.quest import Quest  # noqa: F401
from ds_common.models.rules_reaction import PlayerRulesReaction  # noqa: F401
from ds_common.models.session_memory import SessionMemory  # noqa: F401
from ds_common.models.skill import Skill  # noqa: F401
from ds_common.models.world_event import WorldEvent  # noqa: F401
from ds_common.models.world_item import WorldItem  # noqa: F401
from ds_common.models.world_memory import WorldMemory  # noqa: F401
from ds_common.models.world_region import WorldRegion  # noqa: F401
