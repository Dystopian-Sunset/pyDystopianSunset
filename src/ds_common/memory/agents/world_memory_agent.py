"""World memory promotion agent for creating permanent world lore."""

from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

ImpactLevel = Literal["minor", "moderate", "major", "world_changing"]


class WorldNarrative(BaseModel):
    """Permanent world memory narrative."""

    title: str = Field(description="Memory title (5-150 characters)", min_length=5, max_length=150)
    description: str = Field(
        description="Concise description (50-500 characters)",
        min_length=50,
        max_length=500,
    )
    full_narrative: str = Field(
        description="Rich detail narrative (200-3000 characters)",
        min_length=200,
        max_length=3000,
    )
    related_entities: dict[str, list[str]] = Field(
        description="Related entities: {characters: [], locations: [], factions: []}",
        default_factory=dict,
    )
    tags: list[str] = Field(description="Tags for categorization", default_factory=list)
    impact_level: ImpactLevel = Field(description="Impact level of this memory")
    is_public: bool = Field(
        description="Whether this memory is publicly discoverable", default=True
    )
    discovery_requirements: dict | None = Field(
        description="Requirements for discovering this memory",
        default=None,
    )
    consequences: list[str] = Field(
        description="Consequences or ripple effects of this event",
        default_factory=list,
    )


def _get_agent_config():
    """Get agent configuration from config system or environment variables."""
    try:
        from ds_common.config_bot import get_config

        config = get_config()
        base_url = config.ai_gm_base_url
        model_name = config.ai_gm_model_name
        api_key = config.ai_gm_api_key or "sk-ollama-local-dummy-key-not-used"
        return base_url, model_name, api_key
    except ImportError:
        import os

        base_url = (
            os.getenv("DS_AI_GM_BASE_URL")
            or os.getenv("DB_GM_BASE_URL")
            or "http://localhost:11434/v1"
        )
        api_key = (
            os.getenv("DS_AI_GM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or "sk-ollama-local-dummy-key-not-used"
        )
        model_name = (
            os.getenv("DS_AI_GM_MODEL_NAME") or os.getenv("DB_GM_MODEL_NAME") or "gpt-oss:latest"
        )
        return base_url, model_name, api_key


_world_memory_agent: Agent | None = None


def _get_world_memory_agent() -> Agent:
    """Get or create the world memory agent with configuration."""
    global _world_memory_agent
    if _world_memory_agent is None:
        base_url, model_name, api_key = _get_agent_config()

        world_memory_model = OpenAIModel(
            model_name,
            provider=OpenAIProvider(base_url=base_url, api_key=api_key),
        )
        _world_memory_agent = Agent(
            world_memory_model,
            system_prompt="""You are a world lore archivist for a cyberpunk RPG game world.
Transform high-impact episodes into permanent world memory that becomes part of the game's history.

Responsibilities:
- Establish canonical facts about the world
- Identify ripple effects and consequences
- Create future story hooks
- Maintain lore consistency
- Determine impact level (minor, moderate, major, world_changing)
- Set discovery requirements for secrets

Style:
- Historical record tone
- Focus on facts and consequences
- Highlight what makes this memory significant
- Consider how this affects the world going forward

Create a title, description, full narrative, related entities, tags, impact level, public status, discovery requirements, and consequences.""",
            output_type=WorldNarrative,
        )
    return _world_memory_agent


class _WorldMemoryAgentProxy:
    """Proxy for lazy agent initialization."""

    def __getattr__(self, name: str):
        agent = _get_world_memory_agent()
        return getattr(agent, name)

    async def run(self, *args, **kwargs):
        agent = _get_world_memory_agent()
        return await agent.run(*args, **kwargs)


world_memory_agent = _WorldMemoryAgentProxy()
