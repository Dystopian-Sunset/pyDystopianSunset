import logging

import discord
from discord import Member, User
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
    async def on_member_join(self, member: Member | User):
        self.logger.info("Member joined: %s", member)
        await self.sync_user(member)
        await self.assign_citizen_role(member)

        if not member.dm_channel:
            await member.create_dm()

        await member.dm_channel.send(
            "Welcome to the Quillian Undercity!\n\nI will be your assistant. Type `/help` for detailed help."
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member | User):
        self.logger.info("Member left: %s", member)

        player = await Player.from_db(self.db_game, RecordID("player", member.id))
        if player:
            characters = await player.get_characters(self.db_game)
            for character in characters:
                await character.delete(self.db_game)
            await player.delete(self.db_game)

        if self.bot.channel_bot_logs:
            await self.bot.channel_bot_logs.send(
                f"Member left: {member}, they had {len(characters)} characters. Player data has been purged. Hasta la vista, baby."
            )

    async def sync_users(self):
        self.logger.info("Syncing users...")
        bot_users = 0
        for user in self.bot.users:
            if not user.bot:
                await self.sync_user(user)
                await self.assign_citizen_role(user)
            else:
                bot_users += 1

        self.logger.info(
            f"Synced {len(self.bot.users) - bot_users} users. {bot_users} bots."
        )

    async def sync_user(self, user: Member | User, is_active: bool = True):
        db_user = Player.from_member(user, is_active)

        if not await Player.from_db(self.db_game, RecordID("player", user.id)):
            await db_user.upsert(self.db_game)
        else:
            await db_user.update_last_active(self.db_game)

        self.logger.info(f"Synced user {user}:{user.id}")

    async def assign_citizen_role(self, member: Member | User):
        guild = self.bot.guilds[0]

        if isinstance(member, User) and not isinstance(member, Member):
            member = guild.get_member(member.id)
            if member is None:
                # If not cached, fetch from API
                try:
                    member = await guild.fetch_member(member.id)
                except discord.NotFound:
                    self.logger.warning(f"User {member.id} not found in guild.")
                    return

        citizen_role = discord.utils.get(guild.roles, name="citizen")
        if citizen_role and isinstance(member, Member):
            await member.add_roles(citizen_role)


async def setup(bot: commands.Bot) -> None:
    bot.logger.info("Loading welcome cog...")
    await bot.add_cog(Welcome(bot=bot, db_game=bot.db_game))
