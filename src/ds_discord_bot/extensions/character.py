import logging

import discord
from discord import TextChannel
from discord.ext import commands
from surrealdb import AsyncSurreal

from ds_common.models.character_class import CharacterClass
from ds_common.models.player import Player
from ds_discord_bot.extensions.views.character_class_selection import (
    CharacterClassSelectionView,
)


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

    @commands.group()
    async def character(self, ctx: commands.Context):
        """
        Character commands
        """
        if not ctx.author.dm_channel:
            await ctx.author.create_dm()

        if ctx.invoked_subcommand is None:
            await ctx.author.dm_channel.send(
                "Invalid subcommand. Use `!character <subcommand>`"
            )

    @character.command(name="create")
    async def create_character(self, ctx: commands.Context):
        """
        Create a new character
        """
        player = Player.from_member(ctx.author)
        if (
            len(await player.get_characters(self.db_game))
            >= self.bot.game_settings.max_characters_per_player
        ):
            await ctx.author.dm_channel.send(
                "You have reached the maximum number of characters. Delete an existing character before trying to create a new one."
            )
            return

        embed = discord.Embed(
            title="Character Creation",
            description="To begin character creation, select a character class. Your characters class will determine their core stats and abilities. As you progress through the game, you will be able to upgrade your character's stats and abilities.",
            color=discord.Color.dark_green(),
        )
        view = CharacterClassSelectionView(
            db=self.db_game,
            character_classes=await CharacterClass.get_all(self.db_game),
        )

        await ctx.author.dm_channel.send(embed=embed, view=view)

    @character.command(name="delete")
    async def delete_character(self, ctx: commands.Context, name: str):
        """
        Delete a character
        """
        self.logger.info("Character deleted: %s", ctx.author)

    @character.command(name="list")
    async def list_characters(self, ctx: commands.Context):
        """
        List all characters
        """
        self.logger.info("Character list: %s", ctx.author)

        player = Player.from_member(ctx.author)
        characters = await player.get_characters(self.db_game)
        if not characters:
            await ctx.author.dm_channel.send(
                "You have no characters. Create one with `!character create`"
            )
        else:
            character_string = "Characters:\n"
            for character in characters:
                character_string += f"- {character.name} - {character.id}\n"
            await ctx.author.dm_channel.send(character_string)

    @character.command(name="describe")
    async def describe_character(self, ctx: commands.Context, name: str):
        """
        Get information about a character
        """
        self.logger.info("Character info: %s", ctx.author)

    @character.command(name="use")
    async def use_character(self, ctx: commands.Context, name: str | None = None):
        """
        Use a character
        """
        if name is None:
            # TODO: Select active character using selection view
            return

        await ctx.author.dm_channel.send(
            f"Character {name} selected, you are now playing as {name}"
        )

    @character.command(name="current")
    async def current_character(self, ctx: commands.Context):
        """
        Get the current character
        """
        player = Player.from_member(ctx.author)
        active_character = await player.get_active_character(self.db_game)
        if active_character:
            await ctx.author.dm_channel.send(
                f"You are currently playing as {active_character.name}"
            )
        else:
            await ctx.author.dm_channel.send("You are not playing as any character")


async def setup(bot: commands.Bot) -> None:
    bot.logger.info("Loading character cog...")
    await bot.add_cog(Character(bot=bot, db_game=bot.db_game))
