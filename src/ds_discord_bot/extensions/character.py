import logging

import discord
from discord import TextChannel, app_commands
from discord.ext import commands
from surrealdb import AsyncSurreal

from ds_common.models.character_class import CharacterClass
from ds_common.models.player import Player
from ds_discord_bot.extensions.views.character_class_selection import (
    CharacterClassSelectionView,
)
from ds_discord_bot.extensions.views.character_widget import CharacterWidget


class Character(commands.Cog):
    def __init__(self, bot: commands.Bot, db_game: AsyncSurreal):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.bot: commands.Bot = bot
        self.db_game: AsyncSurreal = db_game
        self.character_creation_channel: TextChannel | None = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.character_creation_channel = await self.bot.get_channel(
            "🔥-character-foundry"
        )

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
        """
        Create a new character
        """
        player = Player.from_member(interaction.user)

        if not interaction.user.dm_channel:
            await interaction.user.create_dm()

        characters = await player.get_characters(self.db_game)
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
            db=self.db_game,
            character_classes=await CharacterClass.get_all(self.db_game),
        )

        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send(embed=embed, view=view)

    @character.command(name="delete", description="Delete a character")
    @app_commands.describe(name="The name of the character to delete")
    async def delete_character(self, interaction: discord.Interaction, name: str):
        """
        Delete a character
        """
        player = Player.from_member(interaction.user)
        characters = await player.get_characters(self.db_game)

        if not characters:
            await interaction.response.send_message(
                "You have no characters. Create one with `/character create`",
                ephemeral=True,
            )
        else:
            for character in characters:
                if character.name.lower() == name.lower():
                    await character.delete(self.db_game)
                    await interaction.response.send_message(
                        f"Character {name} deleted successfully!", ephemeral=True
                    )
                    return

            await interaction.response.send_message(
                f"Character {name} not found.", ephemeral=True
            )

    @character.command(name="list", description="List all characters")
    async def list_characters(self, interaction: discord.Interaction):
        """
        List all characters
        """
        self.logger.info("Character list: %s", interaction.user)

        player = Player.from_member(interaction.user)
        characters = await player.get_characters(self.db_game)
        if not characters:
            await interaction.response.send_message(
                "You have no characters. Create one with `/character create`",
                ephemeral=True,
            )
        else:
            active_character = await player.get_active_character(self.db_game)

            embeds = []
            for character in characters:
                character_class = await character.character_class(self.db_game)
                embeds.append(
                    CharacterWidget(
                        character=character,
                        character_class=character_class,
                        is_active=character.id == active_character.id,
                    )
                )

            await interaction.response.send_message(
                embeds=embeds,
            )

    @character.command(name="describe", description="Get information about a character")
    @app_commands.describe(name="The name of the character to describe")
    async def describe_character(self, interaction: discord.Interaction, name: str):
        """
        Get information about a character
        """
        self.logger.info("Character info: %s", interaction.user)

    @character.command(name="use", description="Use a character")
    @app_commands.describe(name="The name of the character to use")
    async def use_character(
        self, interaction: discord.Interaction, name: str | None = None
    ):
        """
        Use a character
        """
        if name is None:
            # TODO: Select active character using selection view
            return

        await interaction.response.send_message(
            f"Character {name} selected, you are now playing as {name}"
        )

    @character.command(name="current", description="Get the current character")
    async def current_character(self, interaction: discord.Interaction):
        """
        Get the current character
        """
        player = Player.from_member(interaction.user)
        active_character = await player.get_active_character(self.db_game)
        if active_character:
            character_class = await active_character.character_class(self.db_game)
            await interaction.response.send_message(
                embed=CharacterWidget(
                    character=active_character,
                    character_class=character_class,
                    is_active=True,
                )
            )
        else:
            characters = await player.get_characters(self.db_game)
            if not characters:
                await interaction.response.send_message(
                    "You have no characters. Create one with `/character create`",
                    ephemeral=True,
                )
            else:
                await player.set_active_character(self.db_game, characters[0])
                await interaction.response.send_message(
                    f"You are now playing as {characters[0].name}"
                )


async def setup(bot: commands.Bot) -> None:
    bot.logger.info("Loading character cog...")
    await bot.add_cog(Character(bot=bot, db_game=bot.db_game))
