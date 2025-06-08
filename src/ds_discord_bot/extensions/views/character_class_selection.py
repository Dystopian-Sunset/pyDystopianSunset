import logging

import discord
from discord.ui import Select, View

from ds_common.models.character_class import CharacterClass
from ds_common.strings import ellipsize
from ds_discord_bot.extensions.dialogs.character_creation_modal import (
    CharacterCreationModal,
)
from ds_discord_bot.surreal_manager import SurrealManager


class CharacterClassSelection(Select):
    def __init__(
        self,
        surreal_manager: SurrealManager,
        character_classes: list[CharacterClass],
        character_creation_channel: discord.TextChannel | None = None,
    ):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.surreal_manager: SurrealManager = surreal_manager
        self.character_creation_channel: discord.TextChannel | None = (
            character_creation_channel
        )

        options = [
            discord.SelectOption(
                label=character_class.name,
                description=ellipsize(character_class.description),
                emoji=character_class.emoji,
                value=str(character_class.id),
            )
            for character_class in character_classes
        ]

        super().__init__(placeholder="Select a character class", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            CharacterCreationModal(
                surreal_manager=self.surreal_manager,
                character_class_id=self.values[0],
                character_creation_channel=self.character_creation_channel,
            )
        )


class CharacterClassSelectionView(View):
    def __init__(
        self,
        surreal_manager: SurrealManager,
        character_classes: list[CharacterClass],
        character_creation_channel: discord.TextChannel | None = None,
    ):
        super().__init__(timeout=300)  # 5 minutes
        self.add_item(
            CharacterClassSelection(
                surreal_manager=surreal_manager,
                character_classes=character_classes,
                character_creation_channel=character_creation_channel,
            )
        )
