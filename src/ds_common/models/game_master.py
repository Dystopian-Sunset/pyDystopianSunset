from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ds_common.models.character import Character
from ds_common.models.character_class import CharacterClass
from ds_common.models.game_session import GameSession
from ds_common.models.player import Player
from ds_common.models.surreal_model import BaseSurrealModel
from ds_discord_bot.surreal_manager import SurrealManager


class GMHistory(BaseSurrealModel):
    game_session_id: str
    player_id: str
    action_character: str | None = None
    characters: list[str] | None = None
    request: str
    model_messages: list[dict]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(table_name="gm_history")


@dataclass
class GMAgentDependencies:
    surreal_manager: SurrealManager
    game_session: GameSession
    player: Player
    characters: dict[Character, CharacterClass]
    action_character: Character | None = None


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
