import discord
from discord.ui import Select, View

from ds_common.models.character import Character
from ds_common.models.character_class import CharacterClass
from ds_common.repository.player import PlayerRepository
from ds_discord_bot.surreal_manager import SurrealManager


class CharacterSelection(Select):
    def __init__(
        self,
        surreal_manager: SurrealManager,
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
        player_repository = PlayerRepository(self.surreal_manager)
        player = await player_repository.get_by_discord_id(interaction.user.id)
        await player.set_active_character(self.surreal_manager, self.values[0])
        await interaction.followup.send(
            f"Character {self.values[0]} selected, you are now playing as {self.values[0]}",
            ephemeral=True,
        )


class CharacterSelectionView(View):
    def __init__(
        self,
        surreal_manager: SurrealManager,
        characters: list[tuple[Character, CharacterClass]],
        active_character: Character | None = None,
        interaction: discord.Interaction | None = None,
    ):
        super().__init__(timeout=300)  # 5 minutes

        self.add_item(
            CharacterSelection(
                surreal_manager=surreal_manager,
                characters=characters,
                active_character=active_character,
                interaction=interaction,
            )
        )
