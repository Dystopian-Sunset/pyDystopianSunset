"""
Base utilities for AI tools to reduce code duplication.

Provides helper functions for common patterns like character resolution
and repository creation.
"""

from typing import TYPE_CHECKING

from pydantic_ai import RunContext

if TYPE_CHECKING:
    from ds_common.models.character import Character
    from ds_common.models.game_master import BaseRequest, GMAgentDependencies
    from ds_discord_bot.postgres_manager import PostgresManager


def get_character_from_context(
    ctx: RunContext["GMAgentDependencies"],
    request: "BaseRequest",
) -> "Character":
    """
    Get character from context with fallback to request.

    Centralizes the pattern:
    character = ctx.deps.action_character or request.character
    if not character:
        raise ValueError("No character available")

    Args:
        ctx: The agent run context with dependencies
        request: The request object that may contain a character

    Returns:
        The character from context or request

    Raises:
        ValueError: If no character is available
    """
    character = ctx.deps.action_character
    if not character:
        character = getattr(request, "character", None)
    if not character:
        raise ValueError("No character available")
    return character


def get_repositories(
    postgres_manager: "PostgresManager",
) -> dict[str, object]:
    """
    Create commonly used repositories.

    Args:
        postgres_manager: The postgres manager instance

    Returns:
        Dictionary of repository instances keyed by name
    """
    from ds_common.repository.character import CharacterRepository
    from ds_common.repository.encounter import EncounterRepository
    from ds_common.repository.game_session import GameSessionRepository
    from ds_common.repository.quest import QuestRepository

    return {
        "character": CharacterRepository(postgres_manager),
        "quest": QuestRepository(postgres_manager),
        "encounter": EncounterRepository(postgres_manager),
        "game_session": GameSessionRepository(postgres_manager),
    }


async def refresh_character(
    postgres_manager: "PostgresManager",
    character: "Character",
) -> "Character":
    """
    Refresh character from database to ensure up-to-date data.

    Args:
        postgres_manager: The postgres manager instance
        character: The character to refresh

    Returns:
        The refreshed character from the database
    """
    from ds_common.repository.character import CharacterRepository

    character_repository = CharacterRepository(postgres_manager)
    refreshed = await character_repository.get_by_id(character.id)
    if not refreshed:
        raise ValueError(f"Character {character.id} not found")
    return refreshed

