
import os
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from surrealdb import AsyncSurreal

from ds_common.models.game_session import GameSession


@dataclass
class GMContextDependencies:
    db: AsyncSurreal
    game_session: GameSession

class GMContext:
    def __init__(
        self,
        db: AsyncSurreal,
        game_session: GameSession,
        model_name: str = "gemma3:latest",
        base_url: str = "http://localhost:11434/v1",
    ):
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

    def load_prompts(self, base_path: str):
        self.prompts["gm_base"] = Path(f"{base_path}/gm_base.md").read_text()

    async def run(self, message: str, deps: GMContextDependencies) -> str: # TODO: Add character and other dependencies
        result = await self.agent.run(message, message_history=self.messages[-10:] if len(self.messages) > 10 else self.messages, deps=deps)
        self.messages.extend(result.new_messages())
        return result.output