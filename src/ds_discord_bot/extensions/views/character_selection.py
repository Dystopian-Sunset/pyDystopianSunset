import discord
from discord.ui import Select, View
from surrealdb import AsyncSurreal

from ds_common.models.character import Character
from ds_common.models.character_class import CharacterClass
from ds_common.models.player import Player


class CharacterSelection(Select):
    def __init__(
        self,
        db: AsyncSurreal,
        characters: list[tuple[Character, CharacterClass]],
        active_character: Character | None = None,
        interaction: discord.Interaction | None = None,
    ):
        options = [
            discord.SelectOption(
                label=f"{character.name} | lvl: {character.level} | N/A"
                + (" (⭐)" if character.id == active_character.id else ""),
                description=character_class.name,
                emoji=character_class.emoji,
                default=True if character.id == active_character.id else False,
            )
            for character, character_class in characters
        ]

        super().__init__(placeholder="Select a character", options=options)

    async def callback(self, interaction: discord.Interaction):
        player = Player.from_member(interaction.user)
        await player.set_active_character(self.db, self.values[0])
        await interaction.followup.send(
            f"Character {self.values[0]} selected, you are now playing as {self.values[0]}",
            ephemeral=True,
        )

class CharacterSelectionView(View):
    def __init__(
        self,
        db: AsyncSurreal,
        characters: list[tuple[Character, CharacterClass]],
        active_character: Character | None = None,
        interaction: discord.Interaction | None = None,
    ):
        super().__init__(timeout=300)  # 5 minutes

        self.add_item(
            CharacterSelection(
                db=db,
                characters=characters,
                active_character=active_character,
                interaction=interaction,
            )
        )
