import logging
from discord import Member
from discord.ext import commands
from surrealdb import AsyncSurreal, RecordID


class Character(commands.Cog):
    def __init__(self, bot: commands.Bot, db_game: AsyncSurreal):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.bot: commands.Bot = bot
        self.db_game: AsyncSurreal = db_game

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("Character cog loaded")

    @commands.group()
    async def character(self, ctx: commands.Context):
        '''
        Character commands
        '''
        if not ctx.author.dm_channel:
            await ctx.author.create_dm()

        if ctx.invoked_subcommand is None:
            await ctx.author.dm_channel.send("Invalid subcommand. Use `!character <subcommand>`")


    @character.command()
    async def create(self, ctx: commands.Context):
        '''
        Create a new character
        '''
        self.logger.info("Character created: %s", ctx.author)

        # TODO: Check if player has open character slots



        # TODO: Implement character creation dialog

    @character.command()
    async def delete(self, ctx: commands.Context, name: str):
        '''
        Delete a character
        '''
        self.logger.info("Character deleted: %s", ctx.author)

    @character.command()
    async def list(self, ctx: commands.Context):
        '''
        List all characters
        '''
        self.logger.info("Character list: %s", ctx.author)

    @character.command()
    async def info(self, ctx: commands.Context, name: str):
        '''
        Get information about a character
        '''
        self.logger.info("Character info: %s", ctx.author)

    @character.command()
    async def use(self, ctx: commands.Context, name: str):
        '''
        Use a character
        '''
        self.logger.info("Character use: %s", ctx.author)
        await ctx.author.dm_channel.send(f"Character {name} selected, you are now playing as {name}")

    @character.command()
    async def current(self, ctx: commands.Context):
        '''
        Get the current character
        '''
        self.logger.info("Character current: %s", ctx.author)
        await ctx.author.dm_channel.send("Current character: None")


    async def get_player_characters(self, user: Member):
        result = await self.db_game.select(
            RecordID("character", user.id)
        )
        return result


async def setup(bot: commands.Bot) -> None:
    bot.logger.info("Loading character cog...")
    await bot.add_cog(Character(bot=bot, db_game=bot.db_game))
