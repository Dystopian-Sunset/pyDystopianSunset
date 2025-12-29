"""Safeguard detection agent for identifying world-breaking changes."""

from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

ThreatType = Literal["mass_destruction", "faction_change", "location_change", "lore_violation"]
RiskLevel = Literal["low", "medium", "high", "critical"]


class SafeguardAnalysis(BaseModel):
    """Analysis of potential world-breaking changes."""

    requires_snapshot: bool = Field(
        description="Whether a snapshot should be created before this change"
    )
    risk_level: RiskLevel = Field(description="Risk level of this change")
    detected_threats: list[ThreatType] = Field(
        description="Types of threats detected",
        default_factory=list,
    )
    reasoning: str = Field(description="Explanation of the analysis")
    recommended_action: str = Field(description="Recommended action to take")


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


_safeguard_agent: Agent | None = None


def _get_safeguard_agent() -> Agent:
    """Get or create the safeguard agent with configuration."""
    global _safeguard_agent
    if _safeguard_agent is None:
        base_url, model_name, api_key = _get_agent_config()

        safeguard_model = OpenAIModel(
            model_name,
            provider=OpenAIProvider(base_url=base_url, api_key=api_key),
        )
        _safeguard_agent = Agent(
            safeguard_model,
            system_prompt="""You are a safeguard system for a cyberpunk RPG game world.
Analyze proposed world changes to detect potential world-breaking events.

Threats to detect:
- mass_destruction: Destroying cities, killing major NPCs, catastrophic events
- faction_change: Overthrowing governments, changing power structures, major faction shifts
- location_change: Destroying key locations, changing geography, altering important places
- lore_violation: Contradicting established world facts, breaking continuity

Risk levels:
- critical: Would fundamentally break the game world
- high: Major disruption requiring careful consideration
- medium: Significant change that should be reviewed
- low: Minor change, likely safe

If risk_level is high or critical, or if any threats are detected, requires_snapshot should be true.
Provide reasoning and recommended action.""",
            output_type=SafeguardAnalysis,
        )
    return _safeguard_agent


class _SafeguardAgentProxy:
    """Proxy for lazy agent initialization."""

    def __getattr__(self, name: str):
        agent = _get_safeguard_agent()
        return getattr(agent, name)

    async def run(self, *args, **kwargs):
        agent = _get_safeguard_agent()
        return await agent.run(*args, **kwargs)


safeguard_agent = _SafeguardAgentProxy()
