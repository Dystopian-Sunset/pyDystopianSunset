import discord
from discord.ui import Select, View

from ds_common.models.character import Character
from ds_common.models.character_class import CharacterClass
from ds_common.repository.player import PlayerRepository
from ds_discord_bot.postgres_manager import PostgresManager


class CharacterSelection(Select):
    def __init__(
        self,
        postgres_manager: PostgresManager,
        characters: list[tuple[Character, CharacterClass]],
        active_character: Character | None = None,
        interaction: discord.Interaction | None = None,  # noqa: ARG002
    ):
        self.postgres_manager = postgres_manager
        options = [
            discord.SelectOption(
                label=f"{character.name} | lvl: {character.level} | N/A"
                + (" (⭐)" if character.id == active_character.id else ""),
                description=character_class.name,
                emoji=character_class.emoji,
                default=character.id == active_character.id,
            )
            for character, character_class in characters
        ]

        super().__init__(placeholder="Select a character", options=options)

    async def callback(self, interaction: discord.Interaction):
        from uuid import UUID

        player_repository = PlayerRepository(self.postgres_manager)
        player = await player_repository.get_by_discord_id(interaction.user.id)
        if player:
            character_id = UUID(self.values[0])
            character = await player_repository.get_characters(player)
            target_character = next((c for c in character if c.id == character_id), None)
            if target_character:
                await player_repository.set_active_character(player, target_character)
                await interaction.followup.send(
                    f"Character {target_character.name} selected, you are now playing as {target_character.name}",
                    ephemeral=True,
                )


class CharacterSelectionView(View):
    def __init__(
        self,
        postgres_manager: PostgresManager,
        characters: list[tuple[Character, CharacterClass]],
        active_character: Character | None = None,
        interaction: discord.Interaction | None = None,
    ):
        super().__init__(timeout=300)  # 5 minutes

        self.add_item(
            CharacterSelection(
                postgres_manager=postgres_manager,
                characters=characters,
                active_character=active_character,
                interaction=interaction,
            )
        )
