"""Importance scoring agent for real-time event evaluation."""

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider


class ImportanceAnalysis(BaseModel):
    """Analysis of event importance."""

    score: float = Field(description="Importance score from 0.0 to 1.0", ge=0.0, le=1.0)
    reasoning: str = Field(description="Explanation of why this score was assigned")
    should_promote: bool = Field(
        description="Whether this event should be promoted to world memory"
    )
    tags: list[str] = Field(description="Relevant tags for categorization", default_factory=list)
    emotional_valence: float = Field(
        description="Emotional valence from -1.0 (negative) to 1.0 (positive)",
        ge=-1.0,
        le=1.0,
    )


def _get_agent_config():
    """Get agent configuration from config system or environment variables."""
    try:
        from ds_common.config_bot import get_config

        config = get_config()
        base_url = config.ai_gm_base_url
        model_name = config.ai_gm_model_name
        # API key is optional for local services, use dummy if not provided
        api_key = config.ai_gm_api_key or "sk-ollama-local-dummy-key-not-used"
        return base_url, model_name, api_key
    except ImportError:
        # Fallback to environment variables if config not available
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


# Lazy initialization - agent is created on first use
_importance_agent: Agent | None = None


def _get_importance_agent() -> Agent:
    """Get or create the importance agent with configuration."""
    global _importance_agent
    if _importance_agent is None:
        base_url, model_name, api_key = _get_agent_config()

        importance_model = OpenAIModel(
            model_name,
            provider=OpenAIProvider(base_url=base_url, api_key=api_key),
        )
        _importance_agent = Agent(
            importance_model,
            system_prompt="""You are an importance evaluator for a cyberpunk RPG game world.
Analyze events and determine their significance on a scale from 0.0 (trivial) to 1.0 (world-changing).

Scoring guidelines:
- 0.7-1.0: Major plot revelations, world state changes, faction shifts, character deaths
- 0.4-0.6: Character development, quest completion, significant discoveries, relationship changes
- 0.0-0.3: Routine actions, trivial dialogue, minor interactions

Consider:
- Impact on the game world
- Character development significance
- Plot advancement
- Relationship changes
- Discovery of secrets or lore

Return a JSON object with: score (float 0.0-1.0), reasoning (string), should_promote (boolean), tags (array of strings), emotional_valence (float -1.0 to 1.0).""",
            output_type=ImportanceAnalysis,
        )
    return _importance_agent


# Public API - agent is accessed via property to enable lazy initialization
class _ImportanceAgentProxy:
    """Proxy for lazy agent initialization."""

    def __getattr__(self, name: str):
        agent = _get_importance_agent()
        return getattr(agent, name)

    async def run(self, *args, **kwargs):
        agent = _get_importance_agent()
        return await agent.run(*args, **kwargs)


importance_agent = _ImportanceAgentProxy()
