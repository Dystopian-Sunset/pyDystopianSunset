"""
Game extension package.

This package contains the refactored game extension functionality.
"""

import logging
import os
from pathlib import Path

from discord.ext import commands as discord_commands
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from ds_common.config_bot import get_config
from ds_common.models.game_master import GMAgentDependencies

from .ai_tools.base import get_character_from_context, get_repositories, refresh_character
from .commands import GameCommands
from .context_builder import ContextBuilder
from .permission_manager import PermissionManager
from .prompt_service import load_system_prompt, register_system_prompts, register_user_context_prompt
from .session_manager import SessionManager
from .tools import create_tools

# Global variables for agent and prompt loader
# These are set by the setup function and used by GameCommands
agent: Agent | None = None
prompt_loader = None


async def setup(bot: discord_commands.Bot) -> None:
    """
    Setup function for the game extension.

    This function initializes the AI agent, prompt loader, and registers
    all system prompts before adding the GameCommands cog to the bot.

    Args:
        bot: The Discord bot instance
    """
    global agent, prompt_loader

    bot.logger.info("Loading game cog...")

    config = get_config()
    model_name = config.ai_gm_model_name
    base_url = config.ai_gm_base_url
    api_key = config.ai_gm_api_key or "sk-ollama-local-dummy-key-not-used"

    model = OpenAIModel(
        model_name=model_name,
        provider=OpenAIProvider(base_url=base_url, api_key=api_key),
    )

    # Initialize prompt loader for contextual prompts
    # Support configurable prompt theme/path for multi-theme support
    prompt_theme = config.ai_gm_prompt_theme
    
    if prompt_theme and Path(prompt_theme).is_absolute():
        # Full path provided - use it directly
        prompt_base_path = Path(prompt_theme)
    else:
        # Theme name provided - look in extensions/prompts/{theme}/
        # Default to "dystopian_sunset" if not specified
        theme_name = prompt_theme or "dystopian_sunset"
        prompt_base_path = Path(__file__).parent.parent / "prompts" / theme_name
    
    from ds_discord_bot.extensions.prompt_loader import ContextualPromptLoader

    prompt_loader = ContextualPromptLoader(prompt_base_path)
    bot.logger.info(f"Initialized contextual prompt loader (theme: {prompt_theme or 'dystopian_sunset'}, path: {prompt_base_path})")

    # Get system prompt path from config or use default
    env_prompt_path = config.ai_gm_system_prompt_path.strip()
    if env_prompt_path:
        # Legacy mode: use single prompt file
        system_prompt_path = Path(env_prompt_path)
        system_prompt = []
        async for line in load_system_prompt(system_prompt_path):
            system_prompt.append(line)
        base_system_prompt = "\n".join(system_prompt)
        bot.logger.info(f"Using legacy prompt file: {system_prompt_path}")
    else:
        # New modular mode: use minimal base prompt
        # Core modules will be loaded dynamically via system prompts
        game_name = config.game_name
        base_system_prompt = f"You are the Gamemaster for the {game_name} roleplaying game."
        bot.logger.info(f"Using modular prompt system (game: {game_name})")

    # Create tools before creating agent
    tools = create_tools()

    agent = Agent(
        model=model,
        system_prompt=base_system_prompt,
        deps_type=GMAgentDependencies,
        tools=tools,
        retries=3,
    )

    # Register all system prompts
    register_system_prompts(agent, prompt_loader)
    register_user_context_prompt(agent)

    await bot.add_cog(GameCommands(bot=bot, postgres_manager=bot.postgres_manager, agent=agent))


__all__ = [
    "ContextBuilder",
    "GameCommands",
    "PermissionManager",
    "SessionManager",
    "get_character_from_context",
    "get_repositories",
    "refresh_character",
    "setup",
    "agent",
]

