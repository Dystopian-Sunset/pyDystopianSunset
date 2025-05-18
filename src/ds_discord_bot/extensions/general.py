import logging

import discord
from discord import app_commands
from discord.ext import commands
from surrealdb import AsyncSurreal


class General(commands.Cog):
    def __init__(self, bot: commands.Bot, db_game: AsyncSurreal):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.bot: commands.Bot = bot
        self.db_game: AsyncSurreal = db_game

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("General cog loaded")

    @app_commands.command(name="help", description="Get help with the bot")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        help_text = "I will be your humble assistant while you are exploring the Quillian Undercity."
        help_text += "\n\n"
        help_text += "To get started, create a character using `/character create` and begin your journey!\n"
        help_text += "Once you are ready to begin your journey, use `/game start` to start the game. This will create a new game session and allow you to begin your journey. You may use the custom channel to experience the game. Use natural speech to interact within the game world."
        help_text += "\n\n"
        help_text += "If you need help, use `/help` to get help with the bot.\n"
        help_text += "Here is a listing of system commands, grouped by category:\n"

        for command in self.bot.tree.get_commands():
            cog = command.parent
            if cog:
                help_text += f"\n{cog.name}\n"
                help_text += f"\n`/{command.name}` - {command.description}"
            else:
                help_text += f"\n`/{command.name}` - {command.description}"

        help_text += "\n\n"
        help_text += "Each command group has it's own help command. Use `/GROUP help` to get help with a specific command group."

        embed = discord.Embed(
            title="Welcome to the Quillian Undercity Discord Server!",
            description=help_text,
            color=discord.Color.orange(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    bot.logger.info("Loading general cog...")
    await bot.add_cog(General(bot=bot, db_game=bot.db_game))
