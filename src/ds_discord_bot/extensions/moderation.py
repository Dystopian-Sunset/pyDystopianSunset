import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from ds_common.repository.player import PlayerRepository
from ds_discord_bot.surreal_manager import SurrealManager


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot, surreal_manager: SurrealManager):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.bot: commands.Bot = bot
        self.surreal_manager: SurrealManager = surreal_manager

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
            player_repo = PlayerRepository(self.surreal_manager)
            player = await player_repo.get_by_id(user.id)
            if player:
                player.is_active = False
                player.last_active_at = datetime.now(timezone.utc)
                await player_repo.upsert(player)
                self.logger.debug("Deactivated player %s", player)
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
            player_repo = PlayerRepository(self.surreal_manager)
            player = await player_repo.get_by_id(user.id)
            if player:
                player.is_active = True
                player.last_active_at = datetime.now(timezone.utc)
                await player_repo.upsert(player)
                self.logger.debug("Activated player %s", player)
            await interaction.followup.send(f"Unbanned {user}")
        except discord.Forbidden:
            await interaction.followup.send(
                "You do not have permission to unban this user."
            )

    @moderation.command(name="help", description="Get help with moderation commands")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        help_text = ""

        for command in self.bot.commands:
            if command.name == "help":
                continue

            help_text += f"`!{command.name}` - {command.description}\n"

        if self.moderation.commands:
            help_text += "\n\n"

            for command in self.moderation.commands:
                if command.name == "help":
                    continue

                help_text += (
                    f"`/{command.parent.name} {command.name}` - {command.description}\n"
                )

        embed = discord.Embed(
            title="Moderation command help",
            description=help_text,
            color=discord.Color.red(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    bot.logger.info("Loading moderation cog...")
    await bot.add_cog(Moderation(bot=bot, surreal_manager=bot.surreal_manager))
