import logging
from discord.ext import commands
from discord import Member
from surrealdb import AsyncSurreal, RecordID
from datetime import datetime, timezone
from ds_common.models.discord_user import DiscordUser

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

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        self.logger.info("Member left: %s", member)
        await self.sync_user(member, is_active=False)

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
        now = datetime.now(tz=timezone.utc)
        db_user = DiscordUser(
            id=user.id,
            global_name=user.global_name,
            display_name=user.display_name,
            display_avatar=user.display_avatar.url,
            joined_at=now,
            last_active=now,
            is_active=is_active,
        )

        result = await self.db_game.upsert(
            RecordID("player", user.id),
            db_user.model_dump(),
        )

        if not result:
            self.logger.error(f"Failed to sync user {user}:{user.id}")
        else:
            self.logger.info(f"Synced user {user}:{result}")

async def setup(bot: commands.Bot) -> None:
    bot.logger.info("Loading welcome cog...")
    await bot.add_cog(Welcome(bot=bot, db_game=bot.db_game))
