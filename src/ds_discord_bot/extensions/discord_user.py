import logging
from discord.ext import commands


class DiscordUser(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("DiscordUser cog loaded")


async def setup(bot: commands.Bot) -> None:
    bot.logger.info("Loading DiscordUser cog...")
    await bot.add_cog(DiscordUser(bot))
