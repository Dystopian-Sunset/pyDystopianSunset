import logging
import re
from typing import TYPE_CHECKING, Any, override
from uuid import UUID

if TYPE_CHECKING:
    from ds_common.models.game_settings import GameSettings

import discord
from discord import Interaction, ui

# Import models package to ensure all models are registered with SQLAlchemy metadata
import ds_common.models  # noqa: F401
from ds_common.repository.character import CharacterRepository
from ds_common.repository.character_class import CharacterClassRepository
from ds_discord_bot.extensions.views.character_confirmation import (
    CharacterConfirmationView,
    create_character_confirmation_embed,
)
from ds_discord_bot.postgres_manager import PostgresManager


class CharacterCreationModal(ui.Modal, title="Character Creation - Step 3 of 4"):
    character_name = ui.TextInput(
        label="Character Name",
        placeholder="Enter your character's name (3-32 characters, alphanumeric and spaces)",
        min_length=3,
        max_length=32,
        required=True,
    )

    def __init__(
        self,
        postgres_manager: PostgresManager,
        character_class_id: UUID,
        character_creation_channel: discord.TextChannel | None = None,
        game_settings: "GameSettings | Any | None" = None,
        selected_gender: str | None = None,
    ):
        super().__init__()

        self.logger: logging.Logger = logging.getLogger(__name__)
        self.postgres_manager = postgres_manager
        self.character_class_id = character_class_id
        self.character_creation_channel = character_creation_channel
        self.game_settings = game_settings
        self.selected_gender = selected_gender

    def validate_name(self, name: str) -> tuple[bool, str | None]:
        """
        Validate character name.
        Returns (is_valid, error_message)
        """
        # Check length
        if len(name) < 3:
            return False, "Character name must be at least 3 characters long."
        if len(name) > 32:
            return False, "Character name must be no more than 32 characters long."

        # Check for valid characters (alphanumeric, spaces, hyphens, underscores)
        if not re.match(r"^[a-zA-Z0-9\s\-_]+$", name):
            return (
                False,
                "Character name can only contain letters, numbers, spaces, hyphens, and underscores.",
            )

        # Check for leading/trailing spaces
        if name.strip() != name:
            return False, "Character name cannot have leading or trailing spaces."

        # Check for multiple consecutive spaces
        if "  " in name:
            return False, "Character name cannot have multiple consecutive spaces."

        return True, None

    @override
    async def on_submit(self, interaction: Interaction) -> None:
        character_repo = CharacterRepository(self.postgres_manager)
        character_class_repo = CharacterClassRepository(self.postgres_manager)

        # Validate name format
        is_valid, error_message = self.validate_name(self.character_name.value)
        if not is_valid:
            await interaction.response.send_message(
                f"❌ Invalid character name: {error_message}\n\n"
                "**Name Requirements:**\n"
                "• 3-32 characters\n"
                "• Letters, numbers, spaces, hyphens, and underscores only\n"
                "• No leading/trailing spaces\n"
                "• No multiple consecutive spaces",
                ephemeral=True,
            )
            return

        # Check if name already exists
        existing_character = await character_repo.get_by_field(
            "name", self.character_name.value, case_sensitive=False
        )
        if existing_character:
            # Suggest alternatives
            suggestions = [
                f"{self.character_name.value}1",
                f"{self.character_name.value}2",
                f"The {self.character_name.value}",
            ]
            await interaction.response.send_message(
                f"❌ Character name '{self.character_name.value}' is already taken.\n\n"
                f"**Suggested alternatives:**\n"
                + "\n".join(f"• {s}" for s in suggestions)
                + "\n\nPlease try again with a different name.",
                ephemeral=True,
            )
            return

        # Get character class for confirmation
        character_class = await character_class_repo.get_by_id(self.character_class_id)
        if not character_class:
            await interaction.response.send_message(
                "❌ Character class not found. Please try again.",
                ephemeral=True,
            )
            return

        # Defer to show confirmation
        await interaction.response.defer(ephemeral=True)

        # Generate initial stats with class weighting
        from ds_discord_bot.extensions.views.character_confirmation import generate_random_stats

        # Get primary stats for this class
        primary_stats_list = await character_class_repo.get_stats(character_class)
        primary_stats = [stat.abbr for stat in primary_stats_list]

        # Generate weighted stats using game_settings
        initial_stats = generate_random_stats(
            primary_stats=primary_stats,
            game_settings=self.game_settings,
        )

        # Create confirmation view with initial stats and gender
        view = CharacterConfirmationView(
            postgres_manager=self.postgres_manager,
            character_name=self.character_name.value,
            character_class_id=self.character_class_id,
            character_creation_channel=self.character_creation_channel,
            initial_stats=initial_stats,
            game_settings=self.game_settings,
            selected_gender=self.selected_gender,
        )

        # Create confirmation embed
        embed = await create_character_confirmation_embed(
            postgres_manager=self.postgres_manager,
            character_name=self.character_name.value,
            character_class=character_class,
            stats=initial_stats,
            gender=self.selected_gender,
        )

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
