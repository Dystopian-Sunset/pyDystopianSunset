import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks
from surrealdb import AsyncSurreal

from ds_common.models.game_session import GameSession
from ds_common.models.player import Player
from ds_common.name_generator import NameGenerator


class Game(commands.Cog):
    def __init__(self, bot: commands.Bot, db_game: AsyncSurreal):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.bot: commands.Bot = bot
        self.db_game: AsyncSurreal = db_game
        self.game_session_category: discord.CategoryChannel | None = None
        self.game_session_join_channel: discord.VoiceChannel | None = None
        self.game_session_text_channels: list[discord.TextChannel] = []
        self.game_session_voice_channels: list[discord.VoiceChannel] = []

        self.active_game_channels: dict[discord.TextChannel, datetime] = {}

        self.check_game_sessions.start()

    @commands.Cog.listener()
    async def on_ready(self):
        self.game_session_category = await self._find_game_session_category()
        self.game_session_join_channel = await self._init_game_session_join_channel()
        self.logger.info("Game cog loaded")

        for session in await GameSession.get_all(self.db_game):
            channel = self.bot.guilds[0].get_channel(session.channel_id)
            if not channel:
                await session.delete(self.db_game)
                continue

            self.active_game_channels[channel] = session.last_active_at

        self.logger.debug(
            f"Loaded {len(self.active_game_channels)} active game sessions from database"
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel in self.game_session_category.text_channels:
            if message.channel in self.active_game_channels:
                self.logger.debug(
                    "Message in active game session channel: %s", message.channel.name
                )
            else:
                self.logger.debug(
                    "Adding missing game session channel to active game channels: %s",
                    message.channel,
                )

            self.active_game_channels[message.channel] = datetime.now(timezone.utc)
            await GameSession.update_last_active_at(self.db_game, message.channel)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if self.game_session_join_channel:
            if after.channel == self.game_session_join_channel:
                self.logger.debug(
                    "Member %s joined game session channel %s", member, after.channel
                )

                await self.create_game_session(member)

    async def cog_unload_async(self):
        self.check_game_sessions.cancel()

        if self.game_session_category:
            for channel in self.game_session_category.channels:
                await self._delete_channel(channel)
                self.logger.debug("Deleted game session channel: %s", channel.name)

        if self.game_session_join_channel:
            await self._delete_channel(self.game_session_join_channel)
            self.logger.debug(
                "Deleted game session join channel: %s",
                self.game_session_join_channel.name,
            )

        self.logger.info("Game cog unloaded")
        await super().cog_unload_async()

    game = app_commands.Group(name="game", description="Game commands")

    @game.command(name="start", description="Start a new game")
    async def start(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        await self.create_game_session(interaction.user)

        await interaction.followup.send("Game session started", ephemeral=True)

    @game.command(name="end", description="End the current game")
    async def end(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        session = await GameSession.is_playing_in(
            self.db_game, Player.from_member(interaction.user)
        )

        if not session:
            await interaction.followup.send(
                "You are not playing in a game", ephemeral=True
            )
            return

        await self.end_game_session(session)

    @game.command(name="help", description="Get help with game commands")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        help_text = ""

        for command in self.bot.commands:
            if command.name == "help":
                continue

            help_text += f"`!{command.name}` - {command.description}\n"

        if self.game.commands:
            help_text += "\n\n"

            for command in self.game.commands:
                if command.name == "help":
                    continue

                help_text += (
                    f"`/{command.parent.name} {command.name}` - {command.description}\n"
                )

        embed = discord.Embed(
            title="Game command help",
            description=help_text,
            color=discord.Color.red(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @tasks.loop(minutes=1.0)
    async def check_game_sessions(self):
        if self.game_session_category:
            db_sessions = await GameSession.get_all(self.db_game)
            db_channel_names = [session.name for session in db_sessions]

            # Delete channels that are not in the found as sessions in the database
            for channel in self.game_session_category.text_channels:
                if channel.name not in db_channel_names:
                    await self._delete_channel(channel)

            for channel in self.game_session_category.text_channels:
                # Add channels that are not in the active game channels
                if channel not in self.active_game_channels:
                    self.active_game_channels[channel] = datetime.now(timezone.utc)

                    self.logger.debug(
                        f"Added active game session channel: {channel.name} to active game channels"
                    )

                # Check if the channel is idle
                channel_age = (
                    datetime.now(timezone.utc) - self.active_game_channels[channel]
                ).total_seconds()
                max_age = self.bot.game_settings.max_game_session_idle_duration * 60

                if channel_age > max_age:
                    session = await GameSession.from_channel(self.db_game, channel)
                    await self.end_game_session(session)

                    del self.active_game_channels[channel]
                else:
                    self.logger.debug(
                        f"Game session channel {channel.name} idle for {int(channel_age)}/{int(max_age)} seconds"
                    )

            # Remove channels from active game
            self.logger.debug(
                f"Checked {len(self.game_session_category.text_channels)} game session channels for idle sessions"
            )

    @check_game_sessions.before_loop
    async def before_check_game_sessions(self):
        await self.bot.wait_until_ready()
        self.logger.info("Started checking game sessions for idle channels")

    async def create_game_session(self, member: discord.Member):
        # Create game session entry in SurrealDB and associate graph with player
        player = Player.from_member(member)
        characters = await player.get_characters(self.db_game)

        if not member.dm_channel:
            await member.create_dm()

        if not characters:
            await member.dm_channel.send(
                "You have no characters. Create one with `/character create`"
            )
            return

        if not await player.get_active_character(self.db_game):
            await member.dm_channel.send(
                "You have no active character. Select one with `/character use`"
            )
            return

        if len(self.active_game_channels) >= self.bot.game_settings.max_game_sessions:
            await member.dm_channel.send(
                "All game sessions are currently in use. Please try again later."
            )
            return

        current_session = await GameSession.is_playing_in(self.db_game, player)
        if current_session:
            channel_name = current_session.name
            channel = await self._find_channel(channel_name)
            if not channel:
                channel = await self._create_text_channel(channel_name)
                await channel.send(
                    f"Missing game session channel has been recreated {member.mention}\n"
                    "Please review the game rules and setup in the #rules channel.\n"
                    "Remember that you can use `/game help` for help with game commands.\n"
                    f"To help ensure the best experience for all players, sessions that have been idle for {self.bot.game_settings.max_game_session_idle_duration} minutes will be automatically deleted."
                )

            await member.move_to(None)

            await member.dm_channel.send(
                f"You are already playing in a game session. Join <#{channel.id}> to continue, or end the session with `/game end`"
            )

            return

        # Generate a new channel name, check DB for duplicates and generate a new name if needed
        channel_name = NameGenerator.generate_cyberpunk_channel_name()

        channel = await self._create_text_channel(channel_name)

        citizen_role = await self.bot.get_role("citizen")
        if citizen_role:
            await channel.set_permissions(
                citizen_role,
                view_channel=False,
                create_instant_invite=False,
                send_messages=False,
                read_messages=True,
                read_message_history=True,
                add_reactions=False,
            )
        else:
            self.logger.warning("citizen role not found")

        moderator_role = await self.bot.get_role("moderator")
        if moderator_role:
            await channel.set_permissions(
                moderator_role,
                view_channel=True,
                send_messages=True,
                read_messages=True,
                read_message_history=True,
                add_reactions=True,
                manage_messages=True,
            )
        else:
            self.logger.warning("moderator role not found")

        # GM_role = await self.bot.get_role("GM")
        # if GM_role:
        #     await channel.set_permissions(
        #         GM_role,
        #         administrator=True,
        #         view_channel=True,
        #         manage_channels=True,
        #         send_messages=True,
        #         read_messages=True,
        #         read_message_history=True,
        #         manage_messages=True,
        #     )
        # else:
        #     self.logger.warning("GM role not found")

        await channel.set_permissions(
            member,
            view_channel=True,
            send_messages=True,
            read_messages=True,
            read_message_history=True,
            add_reactions=True,
            use_application_commands=True,
        )

        await channel.send(
            f"Welcome to your new game session {member.mention}!\n"
            "Please review the game rules and setup in the #rules channel.\n"
            "Remember that you can use `/game help` for help with game commands.\n"
            f"To help ensure the best experience for all players, sessions that have been idle for {self.bot.game_settings.max_game_session_idle_duration} minutes will be automatically deleted."
        )

        channel.slowmode_delay = self.bot.game_settings.game_channel_slowmode_delay
        self.logger.debug(
            f"Set slowmode delay to {self.bot.game_settings.game_channel_slowmode_delay} seconds"
        )

        self.active_game_channels[channel] = datetime.now(timezone.utc)

        game_session = GameSession(
            name=channel_name,
            channel_id=channel.id,
            created_at=datetime.now(timezone.utc),
            last_active_at=datetime.now(timezone.utc),
        )

        await game_session.insert(self.db_game)
        await game_session.add_player(self.db_game, player)

        # Remove member from join channel
        if member.voice:
            await member.move_to(None)

    async def end_game_session(self, session: GameSession):
        """
        End the game session the player is playing in
        """
        for player in await session.players(self.db_game):
            discord_id = player.id.id
            member = self.bot.guilds[0].get_member(discord_id)

            if not member:
                continue

            if not member.dm_channel:
                await member.create_dm()

            await member.dm_channel.send("Game session ending...")

            await member.move_to(None)

        await session.delete(self.db_game)

        channel = await self._find_channel(session.name)
        if channel:
            await channel.delete()

        await member.dm_channel.send("Game session ended!")

    async def _find_game_session_category(
        self, name: str = "Speakeasy"
    ) -> discord.CategoryChannel | None:
        """
        Find the game session category
        """
        if self.game_session_category:
            return self.game_session_category

        for category in self.bot.guilds[0].categories:
            if category.name == name:
                self.logger.debug("Found Game Session category: %s", category)
                self.game_session_category = category
                return category

        self.logger.debug("Game Session category not found")
        return None

    async def _init_game_session_join_channel(self) -> discord.VoiceChannel | None:
        """
        Initialize the game session join channel
        """
        if self.game_session_join_channel:
            return self.game_session_join_channel

        game_session_join_channel = await self._find_channel("Join to Play")

        if not game_session_join_channel:
            game_session_join_channel = await self._create_voice_channel("Join to Play")

            self.logger.debug(
                "Created game session join channel: %s", game_session_join_channel
            )

            # Ensure citizen role can join the channel
            citizen_role = self.bot.guilds[0].get_role("citizen")
            if citizen_role:
                await self.game_session_join_channel.set_permissions(
                    citizen_role, connect=True
                )

            else:
                self.logger.warning("citizen role not found")

            # Ensure GM role can join/monitor the channel
            GM_role = self.bot.guilds[0].get_role("GM")
            if GM_role:
                await self.game_session_join_channel.set_permissions(
                    GM_role, move_members=True, view_channel=True
                )

            else:
                self.logger.warning("GM role not found")

        return game_session_join_channel

    async def _find_channel(self, name: str) -> discord.TextChannel | None:
        """
        Find a channel by name
        """
        if self.game_session_category:
            for channel in self.game_session_category.channels:
                if channel.name == name:
                    self.logger.debug("Found game session channel: %s", channel)
                    return channel

        self.logger.debug(f"Game session channel not found: {name}")
        return None

    async def _create_text_channel(self, name: str) -> discord.TextChannel | None:
        """
        Create a text channel in the game session category
        """
        if self.game_session_category:
            if not await self._find_channel(name):
                channel = await self.game_session_category.create_text_channel(name)

                # Ensure channel is at bottom of category
                await channel.edit(
                    position=len(self.game_session_category.channels) - 1
                )

                self.logger.debug("Created game session text channel: %s", name)
                return channel
            else:
                self.logger.debug("Game session text channel already exists: %s", name)
                return None

        self.logger.debug("Game Session category not found, cannot create channel")
        return None

    async def _create_voice_channel(self, name: str) -> discord.VoiceChannel | None:
        """
        Create a voice channel in the game session category
        """
        if self.game_session_category:
            if not await self._find_channel(name):
                channel = await self.game_session_category.create_voice_channel(name)

                # Ensure channel is at bottom of category
                await channel.edit(
                    position=len(self.game_session_category.channels) - 1
                )

                self.logger.debug("Created game session voice channel: %s", name)
                return channel
            else:
                self.logger.debug("Game session voice channel already exists: %s", name)
                return None

        self.logger.debug("Game Session category not found, cannot create channel")
        return None

    async def _delete_channel(
        self, channel: str | discord.TextChannel | discord.VoiceChannel
    ) -> bool:
        """
        Delete a channel in the game session category
        """
        if self.game_session_category:
            if isinstance(channel, str):
                channel = await self._find_channel(channel)

            if channel:
                await channel.delete()

                self.logger.debug("Deleted game session channel: %s", channel.name)
                return True

        self.logger.debug("Game Session category not found, cannot delete channel")
        return False


async def setup(bot: commands.Bot) -> None:
    bot.logger.info("Loading game cog...")
    await bot.add_cog(Game(bot=bot, db_game=bot.db_game))
