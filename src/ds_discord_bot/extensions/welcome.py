import logging
from datetime import datetime, timezone

import discord
from discord import Member, User
from discord.ext import commands

from ds_common.models.player import Player
from ds_common.repository.character import CharacterRepository
from ds_common.repository.game_session import GameSessionRepository
from ds_common.repository.player import PlayerRepository
from ds_discord_bot.surreal_manager import SurrealManager


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot, surreal_manager: SurrealManager):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.bot: commands.Bot = bot
        self.surreal_manager: SurrealManager = surreal_manager

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

        player_repo = PlayerRepository(self.surreal_manager)
        player = await player_repo.get_by_discord_id(member.id)
        character_repo = CharacterRepository(self.surreal_manager)
        game_session_repo = GameSessionRepository(self.surreal_manager)
        if player:
            game_session = await player_repo.get_game_session(player)

            if game_session:
                await game_session_repo.remove_player(player, game_session)
                self.logger.debug(
                    "Removed player %s from game session %s",
                    player,
                    game_session,
                )

            characters = await player_repo.get_characters(player)
            for character in characters:
                await character_repo.delete(character.id)
                self.logger.debug("Deleted character %s", character)

            player.is_active = False
            player.last_active_at = datetime.now(timezone.utc)
            await player_repo.upsert(player)
            self.logger.debug("Deactivated player %s", player)

        if self.bot.channel_bot_logs:
            await self.bot.channel_bot_logs.send(
                f"Member left: {member}, they had {len(characters)} characters. Player data has been deactivated. Hasta la vista, baby."
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
        player_repo = PlayerRepository(self.surreal_manager)
        player = await player_repo.get_by_discord_id(user.id)

        if not player:
            player = Player.from_member(user, is_active)
            self.logger.debug(f"Created player {player}")
        else:
            self.logger.debug(f"Found existing player {player}")

        player.is_active = is_active
        player.last_active_at = datetime.now(timezone.utc)
        player = await player_repo.upsert(player)

        self.logger.debug(f"Synced player {player}")

        if player.is_banned:
            await user.ban()

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
    await bot.add_cog(Welcome(bot=bot, surreal_manager=bot.surreal_manager))
