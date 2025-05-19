import logging

import discord
from discord import app_commands
from discord.ext import commands
from surrealdb import AsyncSurreal


class Player(commands.Cog):
    def __init__(self, bot: commands.Bot, db_game: AsyncSurreal):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.bot: commands.Bot = bot
        self.db_game: AsyncSurreal = db_game

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("Player cog loaded")

    player = app_commands.Group(name="player", description="Player commands")

    @player.command(name="sync", description="Sync users")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        await self.bot.sync_users()
        await interaction.followup.send("Synced users")

    @player.command(name="help", description="Get help with player commands")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        help_text = ""

        for command in self.bot.commands:
            if command.name == "help":
                continue

            help_text += f"`!{command.name}` - {command.description}\n"

        if self.player.commands:
            help_text += "\n\n"

            for command in self.player.commands:
                if command.name == "help":
                    continue

                help_text += (
                    f"`/{command.parent.name} {command.name}` - {command.description}\n"
                )

        embed = discord.Embed(
            title="Player command help",
            description=help_text,
            color=discord.Color.red(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    bot.logger.info("Loading Player cog...")
    await bot.add_cog(Player(bot=bot, db_game=bot.db_game))
