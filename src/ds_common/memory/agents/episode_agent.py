"""Episode summarization agent for condensing session memories into narrative episodes."""

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider


class KeyMoment(BaseModel):
    """A key moment in an episode."""

    timestamp: str = Field(description="When this moment occurred")
    description: str = Field(description="What happened")
    significance: str = Field(description="Why this moment matters")


class RelationshipChange(BaseModel):
    """A change in character relationships."""

    character_a: str = Field(description="First character")
    character_b: str = Field(description="Second character")
    change_type: str = Field(description="Type of change (improved, deteriorated, met, etc.)")
    description: str = Field(description="What changed and why")


class EpisodeSummary(BaseModel):
    """Condensed narrative summary of a game session."""

    title: str = Field(description="Episode title (5-100 characters)", min_length=5, max_length=100)
    one_sentence_summary: str = Field(description="Quick reference summary in one sentence")
    narrative_summary: str = Field(
        description="Narrative summary in 2-3 paragraphs (200-1000 characters)",
        min_length=200,
        max_length=1000,
    )
    key_moments: list[KeyMoment] = Field(
        description="1-10 key moments extracted from the session",
        min_length=1,
        max_length=10,
    )
    relationships_changed: list[RelationshipChange] = Field(
        description="Character relationship changes",
        default_factory=list,
    )
    themes: list[str] = Field(description="Themes identified in the episode", default_factory=list)
    cliffhangers: list[str] = Field(
        description="Unresolved threads or cliffhangers",
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


_episode_agent: Agent | None = None


def _get_episode_agent() -> Agent:
    """Get or create the episode agent with configuration."""
    global _episode_agent
    if _episode_agent is None:
        base_url, model_name, api_key = _get_agent_config()

        episode_model = OpenAIModel(
            model_name,
            provider=OpenAIProvider(base_url=base_url, api_key=api_key),
        )
        _episode_agent = Agent(
            episode_model,
            system_prompt="""You are a narrative summarizer for a cyberpunk RPG game world.
Transform raw session events into a compelling narrative episode summary.

Style guidelines:
- Third-person omniscient perspective
- Noir cyberpunk tone
- Focus on character agency and consequences
- Highlight dramatic moments and tension
- Identify themes and narrative threads

Create a title, one-sentence summary, narrative summary, key moments, relationship changes, themes, and cliffhangers.
The narrative should read like a story chapter, not a game log.""",
            output_type=EpisodeSummary,
        )
    return _episode_agent


class _EpisodeAgentProxy:
    """Proxy for lazy agent initialization."""

    def __getattr__(self, name: str):
        agent = _get_episode_agent()
        return getattr(agent, name)

    async def run(self, *args, **kwargs):
        agent = _get_episode_agent()
        return await agent.run(*args, **kwargs)


episode_agent = _EpisodeAgentProxy()
