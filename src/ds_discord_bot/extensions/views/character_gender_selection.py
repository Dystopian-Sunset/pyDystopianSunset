import logging
from typing import Any
from uuid import UUID

import discord
from discord.ui import Select, View

from ds_discord_bot.extensions.dialogs.character_creation_modal import (
    CharacterCreationModal,
)
from ds_discord_bot.postgres_manager import PostgresManager


class GenderSelection(Select):
    """Select dropdown for character gender - second step in character creation (after class)."""

    def __init__(
        self,
        postgres_manager: PostgresManager,
        selected_class_id: UUID,
        character_creation_channel: discord.TextChannel | None = None,
        game_settings: Any | None = None,
    ):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.postgres_manager = postgres_manager
        self.selected_class_id = selected_class_id
        self.character_creation_channel = character_creation_channel
        self.game_settings = game_settings

        options = [
            discord.SelectOption(
                label="Female",
                value="Female",
                description="Use she/her pronouns",
                emoji="👩",
            ),
            discord.SelectOption(
                label="Male",
                value="Male",
                description="Use he/him pronouns",
                emoji="👨",
            ),
            discord.SelectOption(
                label="Other",
                value="Other",
                description="Use they/them pronouns",
                emoji="🧑",
            ),
        ]

        super().__init__(
            placeholder="Select your character's gender...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        selected_gender = self.values[0]
        # After gender selection, show name modal
        await interaction.response.send_modal(
            CharacterCreationModal(
                postgres_manager=self.postgres_manager,
                character_class_id=self.selected_class_id,
                character_creation_channel=self.character_creation_channel,
                game_settings=self.game_settings,
                selected_gender=selected_gender,
            )
        )


class CharacterGenderSelectionView(View):
    """View for selecting character gender - second step in character creation (after class)."""

    def __init__(
        self,
        postgres_manager: PostgresManager,
        selected_class_id: UUID,
        character_creation_channel: discord.TextChannel | None = None,
        game_settings: Any | None = None,
    ):
        super().__init__(timeout=300)  # 5 minutes
        self.postgres_manager = postgres_manager
        self.selected_class_id = selected_class_id
        self.character_creation_channel = character_creation_channel
        self.game_settings = game_settings

        # Add gender selection dropdown
        self.add_item(
            GenderSelection(
                postgres_manager=postgres_manager,
                selected_class_id=selected_class_id,
                character_creation_channel=character_creation_channel,
                game_settings=game_settings,
            )
        )
