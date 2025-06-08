import logging

import discord
from discord import app_commands
from discord.ext import commands

from ds_discord_bot.surreal_manager import SurrealManager


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot, surreal_manager: SurrealManager):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.bot: commands.Bot = bot
        self.surreal_manager: SurrealManager = surreal_manager

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("Admin cog loaded")

    admin = app_commands.Group(name="admin", description="Admin commands")

    @commands.command(name="sync-commands", description="Sync commands")
    @commands.has_permissions(administrator=True)
    async def text_sync_commands(self, ctx: commands.Context):
        """
        Non slash command variant to force sync commands
        """
        await self.bot.tree.sync()
        await ctx.send("Synced commands...")

    @admin.command(name="sync-commands", description="Sync commands")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_commands(self, interaction: discord.Interaction):
        """
        Slash command variant to force sync commands
        """
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.bot.tree.sync()
        await interaction.followup.send("Synced commands...")

    @admin.command(name="help", description="Get help with admin commands")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        help_text = ""

        for command in self.bot.commands:
            if command.name == "help":
                continue

            help_text += f"`!{command.name}` - {command.description}\n"

        if self.admin.commands:
            help_text += "\n\n"

            for command in self.admin.commands:
                if command.name == "help":
                    continue

                help_text += (
                    f"`/{command.parent.name} {command.name}` - {command.description}\n"
                )

        embed = discord.Embed(
            title="Admin command help",
            description=help_text,
            color=discord.Color.red(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    bot.logger.info("Loading admin cog...")
    await bot.add_cog(Admin(bot=bot, surreal_manager=bot.surreal_manager))
