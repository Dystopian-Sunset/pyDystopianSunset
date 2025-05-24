
import json
import logging
import os
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.messages import ModelMessagesTypeAdapter
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from surrealdb import AsyncSurreal

from ds_common.models.game_session import GameSession
from ds_npc.models.gm_memory import GMHistory


@dataclass
class GMContextDependencies:
    db: AsyncSurreal
    game_session: GameSession
    character_name: str

class GMContext:
    def __init__(
        self,
        db: AsyncSurreal,
        game_session: GameSession,
        model_name: str = "gemma3:latest",
        base_url: str = "http://localhost:11434/v1",
    ):
        self.logger = logging.getLogger(__name__)
        self.db = db
        self.game_session = game_session
        self.model_name = model_name
        self.base_url = base_url
        self.prompts = {"gm_base": ""}
        self.messages = []

        self.model = OpenAIModel(
            model_name=self.model_name,  
            provider=OpenAIProvider(base_url=self.base_url)
        )

        self.load_prompts(base_path=f"{os.path.dirname(__file__)}/prompts")

        self.agent = Agent(
            model=self.model,
            deps_type=GMContextDependencies,
            system_prompt=self.prompts["gm_base"],
        )

    @classmethod
    async def create(
        cls,
        db: AsyncSurreal,
        game_session: GameSession,
        model_name: str = "gemma3:latest",
        base_url: str = "http://localhost:11434/v1",
    ):
        self = cls(db, game_session, model_name, base_url)
        await self.load_history()
        return self

    def load_prompts(self, base_path: str) -> None:
        self.logger.debug(f"Loading prompts from {base_path}")
        self.prompts["gm_base"] = Path(f"{base_path}/gm_base.md").read_text()

    async def run(
        self, message: str, deps: GMContextDependencies
    ) -> str:  # TODO: Add character and other dependencies
        self.logger.debug(f"Running agent with message: {message}")
        result = await self.agent.run(message, message_history=self.messages[-10:] if len(self.messages) > 10 else self.messages, deps=deps)

        await self.store_history(deps.character_name, message, result)

        return await self.split_message(result.output)

    async def split_message(self, message: str) -> list[str]:
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

    async def store_history(
        self, character_name: str, request: str, result: AgentRunResult
    ) -> None:
        messages = json.loads(result.new_messages_json())

        self.logger.debug(
            f"Storing history for game session {self.game_session.id}: {messages}"
        )

        gm_history = GMHistory(
            character_name=character_name,
            game_session_id=str(self.game_session.id.id),
            request=request,
            model_messages=messages,
            created_at=datetime.now(timezone.utc),
        )
        try:
            gm_history = GMHistory(
                **await self.db.create(
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

    async def load_history(self) -> None:
        self.logger.debug(f"Loading history for game session {self.game_session.id}")
        query = f"SELECT * FROM gm_history WHERE game_session_id == '{self.game_session.id.id}' ORDER BY created_at DESC LIMIT 10;"
        self.logger.debug("Query: %s", query)
        result = await self.db.query(query)
        result = [GMHistory(**message) for message in result]

        self.messages = []

        for message in result:
            self.logger.debug("Loading history message: %s", message)
            self.messages.extend(
                ModelMessagesTypeAdapter.validate_python(message.model_messages)
            )

        # self.messages = [
        #     ModelMessagesTypeAdapter.validate_python(message["model_messages"])
        #     for message in result
        # ]
