import logging

import discord
from discord import app_commands
from discord.ext import commands

from ds_discord_bot.postgres_manager import PostgresManager


class General(commands.Cog):
    def __init__(self, bot: commands.Bot, postgres_manager: PostgresManager):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.bot: commands.Bot = bot
        self.postgres_manager: PostgresManager = postgres_manager

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("General cog loaded")

    @app_commands.command(name="help", description="Get help with the bot")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        from ds_common.config_bot import get_config

        config = get_config()
        game_name = config.game_name

        help_text = (
            f"I will be your humble assistant while you are exploring the {game_name}."
        )
        help_text += "\n\n"
        help_text += (
            "To get started, create a character using `/character create` and begin your journey!\n"
        )
        help_text += "Once you are ready to begin your journey, use `/game start` to start the game. This will create a new game session and allow you to begin your journey. You may use the custom channel to experience the game. Use natural speech to interact within the game world."
        help_text += "\n\n"
        help_text += "If you need help, use `/help` to get help with the bot.\n"
        help_text += "Here is a listing of system commands, grouped by category:\n"

        for command in self.bot.tree.get_commands():
            if command.name == "help":
                # Skip the root level help command as it's redundant in this context
                continue

            cog = command.parent
            if cog:
                help_text += f"\n{cog.name}\n"
                help_text += f"\n`/{command.name}` - {command.description}"
            else:
                help_text += f"\n`/{command.name}` - {command.description}"

        help_text += "\n\n"
        help_text += "Each command group has it's own help command. Use `/GROUP help` to get help with a specific command group."

        embed = discord.Embed(
            title=f"Welcome to the {game_name} Discord Server!",
            description=help_text,
            color=discord.Color.orange(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    bot.logger.info("Loading general cog...")
    await bot.add_cog(General(bot=bot, postgres_manager=bot.postgres_manager))
