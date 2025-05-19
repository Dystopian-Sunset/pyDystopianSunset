import logging
from typing import override

import discord
from discord import Interaction, ui
from surrealdb import AsyncSurreal, RecordID

from ds_common.models.character import Character
from ds_common.models.character_class import CharacterClass
from ds_common.models.player import Player


class CharacterCreationModal(ui.Modal, title="Character Creation"):
    character_name = ui.TextInput(
        label="Character Name", placeholder="Enter your character's name"
    )

    def __init__(
        self,
        db: AsyncSurreal,
        character_class_id: int | str | RecordID,
        character_creation_channel: discord.TextChannel | None = None,
    ):
        super().__init__()

        self.logger: logging.Logger = logging.getLogger(__name__)
        self.db = db
        self.character_class_id = character_class_id
        self.character_creation_channel = character_creation_channel

    @override
    async def on_submit(self, interaction: Interaction) -> None:
        character = None
        try:
            # Defer the response first to prevent interaction timeout
            await interaction.response.defer(ephemeral=True, thinking=True)

            character_class = await CharacterClass.from_db(
                db=self.db, id=self.character_class_id
            )
            character = await Character.generate_character(
                name=self.character_name.value,
            )

            player = Player.from_member(interaction.user)

            await character.insert(self.db)
            await character.set_class(self.db, character_class)
            await player.relate_character(self.db, character)

            if await player.get_active_character(self.db) is None:
                await player.set_active_character(self.db, character)

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
            interaction.client.logger.error(
                f"Error in character creation: {str(e)}", exc_info=True
            )

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
                await character.delete(self.db)
