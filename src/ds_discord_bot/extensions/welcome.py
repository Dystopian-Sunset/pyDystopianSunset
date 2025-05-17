import logging

from discord import Member
from discord.ext import commands
from surrealdb import AsyncSurreal, RecordID

from ds_common.models.player import Player


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot, db_game: AsyncSurreal):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.bot: commands.Bot = bot
        self.db_game: AsyncSurreal = db_game

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("Welcome cog loaded")
        await self.sync_users()

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        self.logger.info("Member joined: %s", member)
        await self.sync_user(member)

        if not member.dm_channel:
            await member.create_dm()

        await member.dm_channel.send(
            "Welcome to the Quillian Undercity!\n\nI will be your assistant. Type `!help` for help."
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        self.logger.info("Member left: %s", member)
        await self.sync_user(member, is_active=False)
        await member.dm_channel.send("Goodbye! We hope to see you again.")

    async def sync_users(self):
        self.logger.info("Syncing users...")
        bot_users = 0
        for user in self.bot.users:
            if not user.bot:
                await self.sync_user(user)
            else:
                bot_users += 1

        self.logger.info(
            f"Synced {len(self.bot.users) - bot_users} users. {bot_users} bots."
        )

    async def sync_user(self, user: Member, is_active: bool = True):
        db_user = Player.from_member(user, is_active)

        if not await Player.from_db(self.db_game, RecordID("player", user.id)):
            await db_user.upsert(self.db_game)
        else:
            await db_user.update_last_active(self.db_game)

        self.logger.info(f"Synced user {user}:{user.id}")


async def setup(bot: commands.Bot) -> None:
    bot.logger.info("Loading welcome cog...")
    await bot.add_cog(Welcome(bot=bot, db_game=bot.db_game))
