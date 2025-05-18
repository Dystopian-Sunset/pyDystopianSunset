import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks
from surrealdb import AsyncSurreal

from ds_common.models.player import Player


class Game(commands.Cog):
    def __init__(self, bot: commands.Bot, db_game: AsyncSurreal):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.bot: commands.Bot = bot
        self.db_game: AsyncSurreal = db_game

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("Game cog loaded")

    game = app_commands.Group(name="game", description="Game commands")

    @game.command(name="help", description="Get help with the bot")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        help_text = "..."

        embed = discord.Embed(
            title="Game command help",
            description=help_text,
            color=discord.Color.orange(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @game.command(name="start", description="Start a new game")
    async def start(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        player = Player.from_member(interaction.user)
        characters = await player.get_characters(self.db_game)

        if not characters:
            await interaction.followup.send(
                "You have no characters. Create one with `/character create`",
                ephemeral=True,
            )
            return

        active_character = await player.get_active_character(self.db_game)

        if not active_character:
            await interaction.followup.send(
                "You have no active character. Select one with `/character use`",
                ephemeral=True,
            )
            return

        # TODO: Start a new game

        # TODO: Create a private channel for the game session and invite the player to it

        # TODO: Join the private channel for the game session

        # TODO: Send a message to the game channel reviewing the game rules and setup

        await interaction.followup.send("Game started", ephemeral=True)

    @game.command(name="end", description="End the current game")
    async def end(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        # TODO: End the current game session

        # TODO: Delete the private channel for the game session

        await interaction.followup.send("Game ended", ephemeral=True)


    @tasks.loop(minutes=1.0)
    async def check_game_sessions(self):
        # TODO: Check active game sessions, and if they are inactive for 15 minutes, end them

        pass

    @check_game_sessions.before_loop
    async def before_check_game_sessions(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot) -> None:
    bot.logger.info("Loading game cog...")
    await bot.add_cog(Game(bot=bot, db_game=bot.db_game))
