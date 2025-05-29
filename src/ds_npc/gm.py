
import json
import logging
import os
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.agent import AgentRunResult, RunContext
from pydantic_ai.messages import ModelMessagesTypeAdapter
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from ds_common.models.character import Character
from ds_common.models.game_session import GameSession
from ds_common.models.player import Player
from ds_common.repository.character import CharacterRepository
from ds_common.repository.game_session import GameSessionRepository
from ds_discord_bot.surreal_manager import SurrealManager
from ds_npc.models.gm_memory import GMHistory


@dataclass
class GMAgentDependencies:
    surreal_manager: SurrealManager
    game_session: GameSession
    player: Player
    character: Character


CURRENCY_TYPES = Literal["credit"]
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
    currency: Optional[CURRENCY_TYPES]


class RequestRemoveCredits(BaseModel):
    character: Character
    amount: int
    currency: Optional[CURRENCY_TYPES]


class RequestGetInventory(BaseModel):
    character: Character


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


class GMAgent:
    def __init__(
        self,
        game_session: GameSession,
        surreal_manager: SurrealManager,
        model_name: str = os.getenv("MODEL_NAME", "gemma3:latest"),
        base_url: str = os.getenv("BASE_URL", "http://localhost:11434/v1"),
    ):
        self.logger = logging.getLogger(__name__)
        self.surreal_manager = surreal_manager
        self.game_session = game_session
        self.model_name = model_name
        self.base_url = base_url
        self.prompts = {"gm_base": ""}
        self.messages = []

        self.model = OpenAIModel(
            model_name=self.model_name,  
            provider=OpenAIProvider(base_url=self.base_url)
        )

        self._load_prompts(base_path=f"{os.path.dirname(__file__)}/prompts")

        self.agent = Agent(
            model=self.model,
            deps_type=GMAgentDependencies,
            system_prompt=self.prompts["gm_base"],
        )

        self._register_tools()

    @classmethod
    async def create(
        cls,
        game_session: GameSession,
        surreal_manager: SurrealManager,
        model_name: str = os.getenv("MODEL_NAME", "gemma3:latest"),
        base_url: str = os.getenv("BASE_URL", "http://localhost:11434/v1"),
    ):
        self = cls(game_session, surreal_manager, model_name, base_url)
        await self._load_history()
        return self

    def _load_prompts(self, base_path: str) -> None:
        self.logger.debug(f"Loading prompts from {base_path}")
        self.prompts["gm_base"] = (
            Path(f"{base_path}/gm_base.md").read_text().splitlines()
        )

    async def run(
        self, message: str, deps: GMAgentDependencies
    ) -> str:  # TODO: Add character and other dependencies
        self.logger.debug(f"Running agent with message: {message}")

        enhanced_prompt = f"""
Player Action: {message}

MANDATORY REQUIREMENTS:
1. Call get_character_credits() to check current credits before any credit references
2. Call give_credits() for ANY credit acquisition (loot, buy, craft, quest reward)  
3. Call remove_credits() for ANY credit usage/loss (consume, sell, drop, break)

Current player context: {deps}

Process this action and call ALL required functions. Do not skip any function calls.
"""

        result = await self.agent.run(
            enhanced_prompt,
            message_history=self.messages[-10:]
            if len(self.messages) > 10
            else self.messages,
            deps=deps,
        )

        await self._store_history(deps.character, message, result)

        return await self._split_message(result.output)

    async def _split_message(self, message: str) -> list[str]:
        """
        Splits a message into chunks of 2000 characters or less, preferring to split at sentence boundaries.
        """
        max_length = 2000
        chunks = []
        start = 0
        message_length = len(message)

        while start < message_length:
            end = min(start + max_length, message_length)
            chunk = message[start:end]

            # Try to split at the last sentence-ending punctuation within the chunk
            split_at = max(chunk.rfind("."), chunk.rfind("!"), chunk.rfind("?"))
            if split_at != -1 and end != message_length:
                # Split at the punctuation mark (include it)
                split_point = start + split_at + 1
            else:
                split_point = end

            chunks.append(message[start:split_point].strip())
            start = split_point

        return chunks

    async def _store_history(
        self, character: Character, request: str, result: AgentRunResult
    ) -> None:
        messages = json.loads(result.new_messages_json())

        self.logger.debug(
            f"Storing history for game session {self.game_session.id}: {messages}"
        )

        gm_history = GMHistory(
            game_session_id=str(self.game_session.id.id),
            character_name=character.name,
            request=request,
            model_messages=messages,
            created_at=datetime.now(timezone.utc),
        )
        try:
            gm_history = GMHistory(
                **await self.surreal_manager.db.create(
                    "gm_history",
                    gm_history.model_dump(),
                )
            )
        except Exception:
            self.logger.error(
                f"Failed to store long term history: {traceback.format_exc()}"
            )

        self.messages.extend(result.new_messages())

        # We only keep the last 10 messages in memory
        self.messages = self.messages[-10:]

    async def _load_history(self) -> None:
        self.logger.debug(f"Loading history for game session {self.game_session.id}")
        query = f"SELECT * FROM gm_history WHERE game_session_id == '{self.game_session.id.id}' ORDER BY created_at DESC LIMIT 10;"
        self.logger.debug("Query: %s", query)

        async with self.surreal_manager.get_db() as db:
            result = await db.query(query)
        result = [GMHistory(**message) for message in result]

        self.messages = []

        for message in result:
            self.logger.debug("Loading history message: %s", message)
            self.messages.extend(
                ModelMessagesTypeAdapter.validate_python(message.model_messages)
            )

    def _register_tools(self):
        # @self.agent.tool
        # async def create_npc(
        #     ctx: RunContext[GMAgentDependencies],
        #     request: RequestGenerateNPC,
        # ) -> NPC:
        #     """
        #     Select existing NPC or create a new NPC for the player to interact with.
        #     """
        #     print(
        #         f"!!! Selecting or creating NPC: {request.name}, {request.race}, {request.background}, {request.profession}, {request.faction}, {request.location}"
        #     )
        #     return NPC.generate_npc(
        #         request.name,
        #         request.race,
        #         request.background,
        #         request.profession,
        #         request.faction,
        #         request.location,
        #     )

        @self.agent.tool
        async def get_character_credits(
            ctx: RunContext[GMAgentDependencies],
            request: RequestGetCharacterPurse,
        ) -> int:
            """
            Get the character's credits.
            """
            surreal_manager = ctx.deps.surreal_manager

            game_session_repository = GameSessionRepository(surreal_manager)
            game_session = await game_session_repository.get_by_id(
                ctx.deps.game_session_id
            )

            characters = await game_session_repository.characters(game_session)

            requesting_character = None
            for character in characters:
                if character.name == request.character_name:
                    requesting_character = character
                    break

            if not requesting_character:
                raise ValueError(f"Character {request.character_name} not found")

            print(f"!!! Player credits: {requesting_character.credits}")

            return requesting_character.credits

        @self.agent.tool
        async def give_credits(
            ctx: RunContext[GMAgentDependencies],
            request: RequestAddCredits,
        ) -> int:
            """
            Give credits to the character.

            Args:
                ctx: The context of the agent.
                request: The request to give credits.
            """
            if request.amount < 0:
                raise ValueError("Amount must be positive")

            character = ctx.deps.character
            surreal_manager = ctx.deps.surreal_manager

            character_repository = CharacterRepository(surreal_manager)
            character = await character_repository.get_by_id(character.id)

            if not character:
                raise ValueError(f"Character {character.id} not found")

            character.credits += request.amount
            await character_repository.update(character.id, character.model_dump())

            print(
                f"!!! Give credits: {request.amount}, new credits: {character.credits}"
            )

            return character.credits

        @self.agent.tool
        async def take_credits(
            ctx: RunContext[GMAgentDependencies],
            request: RequestAddCredits,
        ) -> int:
            """
            Take credits from the character.

            Args:
                ctx: The context of the agent.
                request: The request to take credits.
            """
            if request.amount < 0:
                raise ValueError("Amount must be positive")

            character = ctx.deps.character
            surreal_manager = ctx.deps.surreal_manager

            character_repository = CharacterRepository(surreal_manager)
            character = await character_repository.get_by_id(character.id)

            if not character:
                raise ValueError(f"Character {character.id} not found")

            if character.credits + request.amount < 0:
                raise ValueError("Not enough credits")

            character.credits -= request.amount
            await character_repository.update(character.id, character.model_dump())

            print(
                f"!!! Take credits: {request.amount}, new credits: {character.credits}"
            )

            return character.credits

        # @self.agent.tool(docstring_format="google", require_parameter_descriptions=True)
        # async def add_character_quest(
        #     ctx: RunContext[GMAgentDependencies],
        #     quest: Quest,
        # ) -> None:
        #     """
        #     Add a quest to the character.

        #     Args:
        #         ctx: The context of the agent.
        #         quest: The quest to add.
        #     """
        #     character = ctx.deps.character
        #     surreal_manager = ctx.deps.surreal_manager

        #     character_repository = CharacterRepository(surreal_manager)
        #     character = await character_repository.get_by_id(character.id)

        #     if not character:
        #         raise ValueError(f"Character {character.id} not found")

        #     await character_repository.add_character_quest(character, quest)

        #     print(f"!!! Added quest: {quest.name}")
