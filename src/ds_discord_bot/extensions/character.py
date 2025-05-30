import logging

import discord
from discord import TextChannel, app_commands
from discord.ext import commands

from ds_common.models.player import Player
from ds_common.repository.character import CharacterRepository
from ds_common.repository.character_class import CharacterClassRepository
from ds_common.repository.player import PlayerRepository
from ds_discord_bot.extensions.views.character_class_selection import (
    CharacterClassSelectionView,
)
from ds_discord_bot.extensions.views.character_selection import CharacterSelectionView
from ds_discord_bot.extensions.views.character_widget import CharacterWidget
from ds_discord_bot.surreal_manager import SurrealManager


class Character(commands.Cog):
    def __init__(self, bot: commands.Bot, surreal_manager: SurrealManager):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.bot: commands.Bot = bot
        self.surreal_manager: SurrealManager = surreal_manager
        self.character_creation_channel: TextChannel | None = None

    @commands.Cog.listener()
    async def on_ready(self):
        # self.character_creation_channel = await self.bot.get_channel(
        #     "🔥-character-foundry"
        # )

        if self.character_creation_channel:
            self.logger.info(
                f"Character creation channel loaded: {self.character_creation_channel.name} (ID: {self.character_creation_channel.id})"
            )
        else:
            self.logger.error("Character creation channel not found")

        self.logger.info("Character cog loaded")

    character = app_commands.Group(name="character", description="Character commands")

    @character.command(name="create", description="Create a new character to play as")
    async def create_character(self, interaction: discord.Interaction):
        player = Player.from_member(interaction.user)
        player_repository = PlayerRepository(self.surreal_manager)

        if not interaction.user.dm_channel:
            await interaction.user.create_dm()

        characters = await player_repository.get_characters(player)
        if len(characters) >= self.bot.game_settings.max_characters_per_player:
            await interaction.response.send_message(
                "You have reached the maximum number of characters. Delete an existing character before trying to create a new one. Use `/character delete` to delete a character.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="Character Creation",
            description="To begin character creation, select a character class. Your characters class will determine their core stats and abilities. As you progress through the game, you will be able to upgrade your character's stats and abilities.",
            color=discord.Color.orange(),
        )

        view = CharacterClassSelectionView(
            surreal_manager=self.surreal_manager,
            character_classes=await CharacterClassRepository(
                self.surreal_manager
            ).get_all(),
            character_creation_channel=self.character_creation_channel,
        )

        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @character.command(name="delete", description="Delete a character")
    @app_commands.describe(name="The name of the character to delete")
    async def delete_character(self, interaction: discord.Interaction, name: str):
        player = Player.from_member(interaction.user)
        player_repository = PlayerRepository(self.surreal_manager)
        character_repository = CharacterRepository(self.surreal_manager)
        characters = await player_repository.get_characters(player)

        if not characters:
            await interaction.response.send_message(
                "You have no characters. Create one with `/character create`",
                ephemeral=True,
            )
        else:
            game_session = await character_repository.get_game_session(characters[0])
            if game_session:
                await interaction.response.send_message(
                    "You are currently in a game session. Please leave it with `/game end` before deleting a character.",
                    ephemeral=True,
                )
                return

            # TODO: Add a confirmation modal type DELETE Name to confirm deletion
            for character in characters:
                if character.name.lower() == name.lower():
                    await character_repository.delete(character.id)
                    await interaction.response.send_message(
                        f"Character {name} deleted successfully!", ephemeral=True
                    )
                    return

            await interaction.response.send_message(
                f"Character {name} not found.", ephemeral=True
            )

    @character.command(name="list", description="List all your characters")
    async def list_characters(self, interaction: discord.Interaction):
        self.logger.info("Character list: %s", interaction.user)

        player = Player.from_member(interaction.user)
        player_repository = PlayerRepository(self.surreal_manager)
        character_repository = CharacterRepository(self.surreal_manager)
        characters = await player_repository.get_characters(player)
        if not characters:
            await interaction.response.send_message(
                "You have no characters. Create one with `/character create`",
                ephemeral=True,
            )
        else:
            active_character = await player_repository.get_active_character(player)

            embeds = []
            for character in characters:
                character_class = await character_repository.get_character_class(
                    character
                )
                embeds.append(
                    CharacterWidget(
                        character=character,
                        character_class=character_class,
                        is_active=character.id == active_character.id,
                    )
                )

            await interaction.response.send_message(
                embeds=embeds,
                ephemeral=True,
            )

    @character.command(
        name="use", description="Select a character to use as your active character"
    )
    @app_commands.describe(name="The name of the character to use")
    async def use_character(
        self, interaction: discord.Interaction, name: str | None = None
    ):
        player = Player.from_member(interaction.user)
        player_repository = PlayerRepository(self.surreal_manager)
        character_repository = CharacterRepository(self.surreal_manager)

        session = await player_repository.get_game_session(player)
        if session:
            await interaction.response.send_message(
                "You are already in a game session. Please leave it with `/game leave` before switching characters.",
                ephemeral=True,
            )
            return

        max_characters = self.bot.game_settings.max_characters_per_player
        if max_characters == 1:
            await interaction.response.send_message(
                "You can only have one character, it will be used automatically.",
                ephemeral=True,
            )

            characters = await player_repository.get_characters(player)
            await player_repository.set_active_character(player, characters[0])
            return

        if name is None:
            characters = await player_repository.get_characters(player)
            active_character = await player_repository.get_active_character(player)

            if not characters:
                await interaction.response.send_message(
                    "You have no characters. Create one with `/character create`",
                    ephemeral=True,
                )
                return
            elif len(characters) == 1:
                await player_repository.set_active_character(player, characters[0])
                await interaction.response.send_message(
                    f"You are now playing as {characters[0].name}", ephemeral=True
                )
                return

            view = CharacterSelectionView(
                surreal_manager=self.surreal_manager,
                characters=[
                    (
                        character,
                        await character_repository.get_character_class(character),
                    )
                    for character in characters
                ],
                active_character=active_character,
                interaction=interaction,
            )

            await interaction.response.send_message(
                "Select a character to use",
                view=view,
                ephemeral=True,
            )
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)

            characters = await player_repository.get_characters(player)
            for character in characters:
                if character.name.lower() == name.lower():
                    await player_repository.set_active_character(player, character)
                    await interaction.followup.send(
                        f"Character {name} selected, you are now playing as {name}",
                        ephemeral=True,
                    )
                    return

            await interaction.followup.send(
                f"Character {name} not found.",
                ephemeral=True,
            )

    @character.command(name="current", description="Get the current character")
    async def current_character(self, interaction: discord.Interaction):
        player = Player.from_member(interaction.user)
        player_repository = PlayerRepository(self.surreal_manager)
        character_repository = CharacterRepository(self.surreal_manager)
        active_character = await player_repository.get_active_character(player)
        if active_character:
            character_class = await character_repository.get_character_class(
                active_character
            )
            await interaction.response.send_message(
                "You are currently playing as",
                embed=CharacterWidget(
                    character=active_character,
                    character_class=character_class,
                    is_active=True,
                ),
                ephemeral=True,
            )
        else:
            characters = await player_repository.get_characters(player)
            if not characters:
                await interaction.response.send_message(
                    "You have no characters. Create one with `/character create`",
                    ephemeral=True,
                )
            else:
                await player_repository.set_active_character(player, characters[0])
                await interaction.response.send_message(
                    f"You are now playing as {characters[0].name}", ephemeral=True
                )

    @character.command(name="help", description="Get help with character commands")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        help_text = ""

        for command in self.bot.commands:
            if command.name == "help":
                continue

            help_text += f"`!{command.name}` - {command.description}\n"

        if self.character.commands:
            help_text += "\n\n"

            for command in self.character.commands:
                if command.name == "help":
                    continue

                help_text += (
                    f"`/{command.parent.name} {command.name}` - {command.description}\n"
                )

        embed = discord.Embed(
            title="Character command help",
            description=help_text,
            color=discord.Color.red(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    bot.logger.info("Loading character cog...")
    await bot.add_cog(Character(bot=bot, surreal_manager=bot.surreal_manager))
