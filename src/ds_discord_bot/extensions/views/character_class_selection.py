import discord
from discord.ui import Select, View
from surrealdb import AsyncSurreal

from ds_common.models.character_class import CharacterClass
from ds_common.strings import ellipsize
from ds_discord_bot.extensions.dialogs.character_creation_modal import (
    CharacterCreationModal,
)


class CharacterClassSelection(Select):
    def __init__(self, db: AsyncSurreal, character_classes: list[CharacterClass]):
        self.db: AsyncSurreal = db

        options = [
            discord.SelectOption(
                label=character_class.name,
                description=ellipsize(character_class.description),
                emoji=character_class.emoji,
                value=str(character_class.id),
                default=True if character_class.id == 1 else False,
            )
            for character_class in character_classes
        ]

        super().__init__(placeholder="Select a character class", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(CharacterCreationModal(db=self.db, character_class_id=self.values[0]))


class CharacterClassSelectionView(View):
    def __init__(self, db: AsyncSurreal, character_classes: list[CharacterClass]):
        super().__init__(timeout=300)  # 5 minutes

        self.add_item(CharacterClassSelection(db=db, character_classes=character_classes))
