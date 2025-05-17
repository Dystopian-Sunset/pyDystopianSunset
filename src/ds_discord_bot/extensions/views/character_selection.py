import discord
from discord.ui import Select, View
from surrealdb import AsyncSurreal

from ds_common.models.character import Character
from ds_discord_bot.extensions.dialogs.character_creation_modal import (
    CharacterCreationModal,
)


class CharacterSelection(Select):
    def __init__(self, db: AsyncSurreal, characters: list[dict]):
        """
        characters: list[dict] = [
            {
                "id": 1,
                "name": "Character 1",
                "class_name": "Class 1",
                "class_emoji": "emoji",
            }
        ]
        """
        self.db: AsyncSurreal = db

        # TODO: Get active character to set default

        # TODO: Get character class to set emoji

        options = [
            discord.SelectOption(
                label=character["name"],
                description=character["class_name"],
                emoji=character["class_emoji"],
                value=str(character["id"]),
                default=True if character["id"] == 1 else False,
            )
            for character in characters
        ]

        super().__init__(placeholder="Select a character", options=options)

    async def callback(self, interaction: discord.Interaction):
        # TODO: Set is_playing_as relation between player and character
        await interaction.response.send_modal(CharacterCreationModal(db=self.db, character_class_id=self.values[0]))


class CharacterSelectionView(View):
    def __init__(self, db: AsyncSurreal, characters: list[Character]):
        super().__init__(timeout=300)  # 5 minutes

        self.add_item(CharacterSelection(db=db, characters=characters))
