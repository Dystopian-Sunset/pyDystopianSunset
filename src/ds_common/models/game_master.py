from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import JSON, Column
from sqlmodel import Field

from ds_common.models.base_model import BaseSQLModel
from ds_common.models.character import Character
from ds_common.models.character_class import CharacterClass
from ds_common.models.game_session import GameSession
from ds_common.models.player import Player
from ds_common.models.quest import Quest
from ds_discord_bot.postgres_manager import PostgresManager


class GMHistory(BaseSQLModel, table=True):
    """
    Game Master history model for storing AI agent interactions
    """

    __tablename__ = "gm_history"

    game_session_id: UUID = Field(foreign_key="game_sessions.id", index=True)
    player_id: UUID | None = Field(default=None, foreign_key="players.id")
    action_character: str | None = Field(default=None, description="Action character ID")
    characters: list[str] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="List of character IDs",
    )
    request: str = Field(description="User request")
    model_messages: list[dict] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="Model response messages",
    )


@dataclass
class GMAgentDependencies:
    postgres_manager: PostgresManager
    game_session: GameSession
    player: Player
    characters: dict[Character, CharacterClass]
    action_character: Character | None = None
    prompt_modules: set[str] | None = None  # Set of prompt module names to load


CURRENCY_TYPES = Literal["quill", "credit"]
INVENTORY_ADD_REASON = Literal[
    "loot",
    "found",
    "bought",
    "crafted",
    "gift",
    "quest_reward",
]
INVENTORY_REMOVE_REASON = Literal[
    "consumed",
    "sold",
    "dropped",
    "broken",
    "quest_turn_in",
]
EQUIPMENT_EQUIP_LOCATION = Literal[
    "head",
    "left_ear",
    "right_ear",
    "neck",
    "shoulders",
    "left_hand",
    "right_hand",
    "chest",
    "back",
    "waist",
    "legs",
    "feet",
]


class RequestGenerateNPC(BaseModel):
    name: str
    race: str
    background: str
    profession: str
    faction: str
    location: str


class RequestGetCharacter(BaseModel):
    character: Character


class RequestGetCharacterPurse(BaseModel):
    character: Character
    currency: CURRENCY_TYPES


class RequestAddCredits(BaseModel):
    character: Character
    amount: int
    currency: CURRENCY_TYPES


class RequestRemoveCredits(BaseModel):
    character: Character
    amount: int
    currency: CURRENCY_TYPES


class ResponseCharacterCredits(BaseModel):
    character: Character
    credits: int
    currency: CURRENCY_TYPES


class RequestGetInventory(BaseModel):
    character: Character


class ResponseInventory(BaseModel):
    character: Character
    inventory: list[dict]


class RequestAddItem(BaseModel):
    character: Character
    item_name: str
    item_quantity: int
    item_type: INVENTORY_ADD_REASON


class RequestRemoveItem(BaseModel):
    character: Character
    item_name: str
    item_quantity: int
    item_type: INVENTORY_REMOVE_REASON


class RequestGetEquipment(BaseModel):
    character: Character
    location: EQUIPMENT_EQUIP_LOCATION


class ResponseEquipment(BaseModel):
    character: Character
    equipment: list[dict]


class RequestSwapEquipment(BaseModel):
    character: Character
    item_name: str
    item_quantity: int
    location: EQUIPMENT_EQUIP_LOCATION


class RequestAddEquipment(BaseModel):
    character: Character
    item_name: str
    item_quantity: int
    location: EQUIPMENT_EQUIP_LOCATION
    item_type: INVENTORY_ADD_REASON


class RequestRemoveEquipment(BaseModel):
    character: Character
    item_name: str
    item_quantity: int
    location: EQUIPMENT_EQUIP_LOCATION
    item_type: INVENTORY_REMOVE_REASON


class RequestGetQuests(BaseModel):
    character: Character


class ResponseQuests(BaseModel):
    character: Character
    quests: list[dict]


class RequestRemoveQuest(BaseModel):
    character: Character
    quest: Quest


class ResponseRemoveQuest(BaseModel):
    character: Character
    quest: Quest
    message: str


class RequestApplyDamage(BaseModel):
    character: Character
    damage_amount: float
    damage_type: str  # "physical", "tech", "environmental"


class RequestApplyHealing(BaseModel):
    character: Character
    heal_amount: float


class RequestConsumeResource(BaseModel):
    character: Character
    resource_type: str  # "stamina" or "tech_power"
    amount: float


class RequestRestoreResource(BaseModel):
    character: Character
    resource_type: str  # "stamina" or "tech_power"
    amount: float


class ResponseCombatStatus(BaseModel):
    character: Character
    health: int
    max_health: int
    stamina: int
    max_stamina: int
    tech_power: int
    max_tech_power: int
    armor: int
    max_armor: int
    is_incapacitated: bool
    status_message: str
    cooldowns: list[dict] | None = (
        None  # [{"type": "ITEM", "name": "item_id", "remaining_hours": 2.5}]
    )


class RequestStartEncounter(BaseModel):
    game_session: GameSession
    encounter_type: str  # "combat", "social", "environmental_hazard"
    description: str | None = None


class RequestEndEncounter(BaseModel):
    encounter_id: str  # UUID as string


class ResponseEncounterStatus(BaseModel):
    encounter_id: str
    encounter_type: str
    status: str
    description: str | None = None
    character_count: int
    npc_count: int


class RequestDistributeRewards(BaseModel):
    encounter_id: str


class ResponseDistributeRewards(BaseModel):
    encounter_id: str
    characters_rewarded: list[
        dict
    ]  # [{"character_id": str, "character_name": str, "exp_gained": int, "leveled_up": bool, "new_level": int}]
    total_exp_distributed: int
    message: str


class RequestSearchCorpse(BaseModel):
    npc_id: str
    character_id: str | None = None


class ResponseSearchCorpse(BaseModel):
    npc_id: str
    character_id: str
    items_found: list[dict]
    credits_found: int
    message: str


class RequestCreateLocationNode(BaseModel):
    location_name: str
    location_type: str  # CITY, DISTRICT, SECTOR, POI, CUSTOM
    description: str | None = None
    theme: str | None = None
    parent_location_name: str | None = None


class ResponseLocationNode(BaseModel):
    location_id: str
    location_name: str
    location_type: str
    message: str


class RequestCreateLocationEdge(BaseModel):
    from_location_name: str
    to_location_name: str
    edge_type: str  # DIRECT, REQUIRES_TRAVEL, SECRET, CONDITIONAL
    travel_method: str | None = None
    travel_time: str | None = None
    narrative_description: str | None = None


class ResponseLocationEdge(BaseModel):
    edge_id: str
    from_location_name: str
    to_location_name: str
    edge_type: str
    message: str


class RequestUpdateCharacterLocation(BaseModel):
    character: Character
    location_name: str


class RequestCheckCooldown(BaseModel):
    character: Character
    cooldown_type: str  # "SKILL", "ABILITY", "ITEM"
    cooldown_name: str


class ResponseCheckCooldown(BaseModel):
    character: Character
    cooldown_type: str
    cooldown_name: str
    is_active: bool
    remaining_hours: float | None = None


class RequestGetCooldowns(BaseModel):
    character: Character


class ResponseGetCooldowns(BaseModel):
    character: Character
    cooldowns: list[dict]  # [{"type": "ITEM", "name": "item_id", "remaining_hours": 2.5}]


class RequestStartCooldown(BaseModel):
    character: Character
    cooldown_type: str  # "SKILL", "ABILITY", "ITEM"
    cooldown_name: str
    duration_game_hours: float


class ResponseStartCooldown(BaseModel):
    character: Character
    cooldown_type: str
    cooldown_name: str
    expires_at_game_time: str
    duration_game_hours: float


class ResponseCharacterLocation(BaseModel):
    character: Character
    location_name: str
    location_id: str | None
    message: str


class RequestFindAndCollectWorldItem(BaseModel):
    character: Character
    item_name: str
    character_location: str | None = None  # Optional: filter by character's current location


class ResponseFindAndCollectWorldItem(BaseModel):
    character: Character
    item_name: str
    found: bool
    collected: bool
    inventory: list[dict]
    message: str
