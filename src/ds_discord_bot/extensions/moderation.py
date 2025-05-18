import logging

import discord
from discord import app_commands
from discord.ext import commands
from surrealdb import AsyncSurreal


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot, db_game: AsyncSurreal):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.bot: commands.Bot = bot
        self.db_game: AsyncSurreal = db_game

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("Moderation cog loaded")

    moderation = app_commands.Group(
        name="moderation", description="Moderation commands"
    )

    @moderation.command(name="kick", description="Kick a user")
    @app_commands.describe(user="The user to kick")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            await user.kick()
            await interaction.followup.send(f"Kicked {user}")
        except discord.Forbidden:
            await interaction.followup.send(
                "You do not have permission to kick this user."
            )

    @moderation.command(name="ban", description="Ban a user")
    @app_commands.describe(user="The user to ban")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            await user.ban()
            await interaction.followup.send(f"Banned {user}")
        except discord.Forbidden:
            await interaction.followup.send(
                "You do not have permission to ban this user."
            )

    @moderation.command(name="unban", description="Unban a user")
    @app_commands.describe(user="The user to unban")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            await user.unban()
            await interaction.followup.send(f"Unbanned {user}")
        except discord.Forbidden:
            await interaction.followup.send(
                "You do not have permission to unban this user."
            )


async def setup(bot: commands.Bot) -> None:
    bot.logger.info("Loading moderation cog...")
    await bot.add_cog(Moderation(bot=bot, db_game=bot.db_game))
