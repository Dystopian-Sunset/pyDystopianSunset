import logging
from typing import override

import discord
from discord import Interaction, ui
from surrealdb import RecordID

from ds_common.models.character import Character
from ds_common.models.player import Player
from ds_common.repository.character import CharacterRepository
from ds_common.repository.character_class import CharacterClassRepository
from ds_common.repository.player import PlayerRepository
from ds_discord_bot.surreal_manager import SurrealManager


class CharacterCreationModal(ui.Modal, title="Character Creation"):
    character_name = ui.TextInput(
        label="Character Name", placeholder="Enter your character's name"
    )

    def __init__(
        self,
        surreal_manager: SurrealManager,
        character_class_id: int | str | RecordID,
        character_creation_channel: discord.TextChannel | None = None,
    ):
        super().__init__()

        self.logger: logging.Logger = logging.getLogger(__name__)
        self.surreal_manager = surreal_manager
        self.character_class_id = character_class_id
        self.character_creation_channel = character_creation_channel

    @override
    async def on_submit(self, interaction: Interaction) -> None:
        character = None
        character_repo = CharacterRepository(self.surreal_manager)
        character_class_repo = CharacterClassRepository(self.surreal_manager)
        player_repo = PlayerRepository(self.surreal_manager)

        try:
            # Defer the response first to prevent interaction timeout
            await interaction.response.defer(ephemeral=True, thinking=True)

            existing_character = await character_repo.get_by_(
                "name", self.character_name.value, case_sensitive=False
            )
            if existing_character:
                await interaction.followup.send(
                    f"Character '{self.character_name.value}' already exists. Please choose a different name.",
                    ephemeral=True,
                )
                return

            character_class = await character_class_repo.get_by_id(
                self.character_class_id
            )
            character = Character.generate_character(
                name=self.character_name.value,
            )

            player = Player.from_member(interaction.user)

            await character_repo.upsert(character)
            await character_repo.set_character_class(character, character_class)
            await player_repo.add_character(player, character)

            if await player_repo.get_active_character(player) is None:
                await player_repo.set_active_character(player, character)

            # Use followup.send instead of response.send_message since we deferred
            await interaction.followup.send(
                f"Character {character.name} created successfully!", ephemeral=True
            )

            if self.character_creation_channel:
                await self.character_creation_channel.send(
                    f"A new {character_class.name}, {character.name}, has joined the world!"
                )
                self.logger.debug(
                    "Sent character creation announcement to %s",
                    self.character_creation_channel,
                )
            else:
                self.logger.debug(
                    "Character creation channel not set, cannot send announcement"
                )

        except Exception as e:
            # Log the error
            self.logger.error(f"Error in character creation: {str(e)}", exc_info=True)

            # Send error message to user
            if interaction.response.is_done():
                await interaction.followup.send(
                    "An error occurred while creating your character. Please try again later.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "An error occurred while creating your character. Please try again later.",
                    ephemeral=True,
                )

            # Remove the character if it was created
            if character:
                await character_repo.delete(character.id)
