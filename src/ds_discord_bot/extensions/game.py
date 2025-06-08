import json
import logging
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

import aiofiles
import aiofiles.os
import discord
from discord import app_commands
from discord.ext import commands, tasks
from pydantic_ai import Agent, RunContext
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.messages import ModelMessagesTypeAdapter
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from ds_common.models.character import Character
from ds_common.models.character_class import CharacterClass
from ds_common.models.game_master import (
    GMAgentDependencies,
    GMHistory,
    RequestAddCredits,
    RequestGenerateNPC,
    RequestGetCharacterPurse,
    ResponseCharacterCredits,
)
from ds_common.models.game_session import GameSession
from ds_common.models.npc import NPC
from ds_common.models.player import Player
from ds_common.models.quest import Quest
from ds_common.name_generator import NameGenerator
from ds_common.repository.character import CharacterRepository
from ds_common.repository.game_session import GameSessionRepository
from ds_common.repository.player import PlayerRepository
from ds_discord_bot.extensions.utils.channels import (
    clean_channel_name,
    create_text_channel,
    delete_channel,
    find_category,
    find_channel,
    move_member_to_voice_channel,
    send_dm,
)
from ds_discord_bot.extensions.utils.messages import send_large_message
from ds_discord_bot.surreal_manager import SurrealManager

model: OpenAIModel | None = None
agent: Agent | None = None


class Game(commands.Cog):
    def __init__(self, bot: commands.Bot, surreal_manager: SurrealManager):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.bot: commands.Bot = bot
        self.surreal_manager: SurrealManager = surreal_manager
        self.game_session_category: discord.CategoryChannel | None = None
        self.game_session_join_channel: discord.VoiceChannel | None = None
        self.game_session_text_channels: list[discord.TextChannel] = []
        self.game_session_voice_channels: list[discord.VoiceChannel] = []
        self.active_game_channels: dict[str, dict] = {}

        self.check_game_sessions.start()

    @commands.Cog.listener()
    async def on_ready(self):
        self.game_session_category = await find_category(
            self.bot, os.getenv("GAME_SESSION_CATEGORY_NAME", "Speakeasy")
        )
        self.game_session_join_channel = await find_channel(
            self.bot,
            os.getenv("GAME_SESSION_JOIN_CHANNEL_NAME", "Join-to-Play"),
            self.game_session_category,
        )
        await self._init_game_sessions()
        self.logger.info("Game cog loaded")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.TextChannel):
        self.logger.debug(f"Guild channel created: {channel}")

        game_session_repository = GameSessionRepository(self.surreal_manager)

        if channel.category == self.game_session_category:
            self.logger.debug(f"Game session channel created: {channel}")
            self.game_session_text_channels.append(channel)

            channel_name = clean_channel_name(channel.name)
            if channel_name not in self.active_game_channels:
                game_session = await game_session_repository.from_channel(channel)
                self.logger.debug(
                    f"Adding missing game session channel to active game channels: {channel.name}"
                )
                self.active_game_channels[channel_name] = {
                    "last_active_at": datetime.now(timezone.utc),
                    "game_session": game_session,
                    "history": list(await self._load_history(game_session)),
                }

                async with channel.typing():
                    characters = await game_session_repository.characters(game_session)
                    character_classes = [
                        f"{character[0].name} ({character[1].name})"
                        for character in characters
                    ]
                    await self._agent_run(
                        game_session=game_session,
                        channel=channel,
                        message=f"The game session has started. The players are [{', '.join(character_classes)}]. The game master is you. Introduce the game session and describe the starting point of the game.",
                        player=None,
                        characters=characters,
                    )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.TextChannel):
        self.logger.debug(f"Guild channel deleted: {channel}")
        if channel.category == self.game_session_category:
            self.logger.debug(f"Game session channel deleted: {channel}")

            if channel in self.game_session_text_channels:
                self.game_session_text_channels.remove(channel)

            if channel in self.game_session_voice_channels:
                self.game_session_voice_channels.remove(channel)

            channel_name = clean_channel_name(channel.name)
            if channel_name in self.active_game_channels:
                self.logger.debug(
                    f"Removing game session channel from active game sessions: {channel.name}"
                )
                del self.active_game_channels[channel_name]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        game_session_repository = GameSessionRepository(self.surreal_manager)

        channel_name = clean_channel_name(message.channel.name)
        if channel_name in self.active_game_channels:
            self.logger.debug(
                f"Message in active game session channel: {message.channel.name}"
            )

            player_repository = PlayerRepository(self.surreal_manager)
            player = await player_repository.get_by_discord_id(message.author.id)
            character = await player_repository.get_active_character(player)

            if not character:
                if not message.author.dm_channel:
                    await message.author.create_dm()

                await send_dm(
                    self.bot,
                    message.author,
                    "You have no active character. Select one with `/character use`",
                )
                return

            game_session = await game_session_repository.from_channel(message.channel)

            if message.content.startswith("!"):
                self.logger.debug(
                    f"Command in active game session channel: {message.channel.name}"
                )

            else:
                async with message.channel.typing():
                    await self._agent_run(
                        game_session=game_session,
                        channel=message.channel,
                        message=message.content,
                        player=player,
                        character=character,
                        characters=await game_session_repository.characters(
                            game_session
                        ),
                    )

            self.active_game_channels[game_session.name]["last_active_at"] = (
                datetime.now(timezone.utc)
            )
            await game_session_repository.update_last_active_at(message.channel)

        else:
            self.logger.warning(
                f"Message in non-active game session channel: {message.channel.name}"
            )

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
                    f"Member {member} joined game session channel {after.channel}"
                )

                await self.create_game_session(member)

    # async def cog_unload_async(self):
    #     self.check_game_sessions.cancel()

    #     if self.game_session_category:
    #         for channel in self.game_session_category.channels:
    #             await self._delete_channel(channel)
    #             self.logger.debug(f"Deleted game session channel: {channel.name}")

    #     if self.game_session_join_channel:
    #         await self._delete_channel(self.game_session_join_channel)
    #         self.logger.debug(
    #             f"Deleted game session join channel: {self.game_session_join_channel.name}",
    #             self.game_session_join_channel.name,
    #         )

    #     self.logger.info("Game cog unloaded")
    #     await super().cog_unload_async()

    game = app_commands.Group(name="game", description="Game commands")

    @game.command(name="start", description="Start a new game")
    @app_commands.describe(
        open_to_all="Whether the game session should be open to all players",
        players="A comma separated list of player names to add to the game session",
    )
    async def start(
        self,
        interaction: discord.Interaction,
        open_to_all: bool = False,
        players: str | None = None,
    ):
        await interaction.response.defer(thinking=True)

        if players:
            players = players.split(",")
            players = [player.strip() for player in players]
            self.logger.info(f"Players: {players}")

        session: GameSession | None = None
        try:
            session = await self.create_game_session(
                interaction.user, open_to_all=open_to_all, players=players
            )
            await interaction.followup.send("Game session started", ephemeral=True)
        except Exception:
            await interaction.followup.send(
                "I'm sorry, but I was unable to start the game session. Please try again later.",
                ephemeral=True,
            )
            self.logger.error(traceback.format_exc())

            try:
                if session:
                    await self.end_game_session(session)
            except Exception:
                self.logger.error(traceback.format_exc())

    @game.command(name="open", description="Open a game session to all players")
    async def open(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        game_session_repository = GameSessionRepository(self.surreal_manager)
        game_session = await game_session_repository.from_channel(interaction.channel)
        if not game_session:
            await interaction.followup.send("Game session not found", ephemeral=True)
            return

        game_session.is_open = True
        await game_session_repository.upsert(game_session)

        channel = await find_channel(self.bot, game_session.name)
        base_channel_name = clean_channel_name(channel.name)
        if channel:
            await channel.edit(name=f"{base_channel_name}")

        await interaction.followup.send("Game session opened", ephemeral=True)

    @game.command(name="close", description="Close a game session to all players")
    async def close(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        game_session_repository = GameSessionRepository(self.surreal_manager)
        game_session = await game_session_repository.from_channel(interaction.channel)
        if not game_session:
            await interaction.followup.send("Game session not found", ephemeral=True)
            return

        game_session.is_open = False
        await game_session_repository.upsert(game_session)

        channel = await find_channel(self.bot, game_session.name)
        base_channel_name = clean_channel_name(channel.name)
        if channel:
            await channel.edit(name=f"🔒-{base_channel_name}")

        await interaction.followup.send("Game session closed", ephemeral=True)

    @game.command(name="end", description="End the current game")
    async def end(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        player_repository = PlayerRepository(self.surreal_manager)
        player = await player_repository.get_by_discord_id(interaction.user.id)

        session = await player_repository.get_game_session(player)
        if not session:
            await interaction.followup.send(
                "You are not playing in a game", ephemeral=True
            )
            return

        await interaction.followup.send("Ending game session", ephemeral=True)

        await self.end_game_session(session)

    @game.command(name="join", description="Join a game session")
    @app_commands.describe(
        game_name="The name of the game session to join",
    )
    async def join(self, interaction: discord.Interaction, game_name: str):
        await interaction.response.defer(ephemeral=True, thinking=True)

        game_session_repository = GameSessionRepository(self.surreal_manager)
        player_repository = PlayerRepository(self.surreal_manager)
        player = await player_repository.get_by_discord_id(interaction.user.id)
        player_character = await player_repository.get_active_character(player)

        if not player_character:
            await interaction.followup.send(
                "You have no active character. Select one with `/character use`",
                ephemeral=True,
            )
            return

        player_session = await player_repository.get_game_session(player)
        if player_session:
            await interaction.followup.send(
                "You are already playing in a game", ephemeral=True
            )
            return

        game_session = await game_session_repository.get_by_(
            field="name", value=game_name
        )
        if not game_session:
            await interaction.followup.send("Game session not found", ephemeral=True)
            return

        if game_session.is_open:
            await game_session_repository.add_player(player, game_session)
            await game_session_repository.add_character(player_character, game_session)

            channel = await find_channel(self.bot, game_session.name)
            if not channel:
                self.logger.warning(
                    f"Channel not found for game session: {game_session.name}"
                )
                return

            await channel.set_permissions(
                interaction.user,
                view_channel=True,
                send_messages=True,
                read_messages=True,
                read_message_history=True,
                add_reactions=True,
                use_application_commands=True,
            )

            character_repository = CharacterRepository(self.surreal_manager)
            character_class = await character_repository.get_character_class(player_character)
            async with channel.typing():
                await self._agent_run(
                    game_session=game_session,
                    channel=channel,
                    message=f"Introduce {player_character.name} ({character_class.name}) to the party. Maintain theme and lore of the game session.",
                    player=player,
                    character=player_character,
                    characters=await game_session_repository.characters(game_session),
                )

        else:
            await interaction.followup.send(
                "Game session is not open to all players", ephemeral=True
            )
            return
        await interaction.followup.send(
            "You have joined the game session", ephemeral=True
        )

    @game.command(name="leave", description="Leave a game session")
    async def leave(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        game_session_repository = GameSessionRepository(self.surreal_manager)
        player_repository = PlayerRepository(self.surreal_manager)
        character_repository = CharacterRepository(self.surreal_manager)

        player = await player_repository.get_by_discord_id(interaction.user.id)
        character = await player_repository.get_active_character(player)

        player_session = await player_repository.get_game_session(player)
        if not player_session:
            await interaction.followup.send(
                "You are not playing in a game", ephemeral=True
            )
            return

        # If last player in session, end the game session
        if len(await game_session_repository.players(player_session)) == 1:
            await self.end_game_session(player_session)
            await interaction.followup.send(
                "Game session ended as there is no one left in the session",
                ephemeral=True,
            )
        else:
            await game_session_repository.remove_player(player, player_session)
            await game_session_repository.remove_character(character, player_session)
            await interaction.followup.send(
                "You have left the game session", ephemeral=True
            )

            channel = await find_channel(self.bot, player_session.name)
            if not channel:
                self.logger.warning(
                    f"Channel not found for game session: {player_session.name}"
                )
                return

            # Remove channel permissions for player
            await channel.set_permissions(
                interaction.user,
                view_channel=False,
                create_instant_invite=False,
                send_messages=False,
                read_messages=True,
                read_message_history=True,
                add_reactions=False,
                use_application_commands=False,
            )

            async with channel.typing():
                await self._agent_run(
                    game_session=player_session,
                    channel=channel,
                    message=f"{character.name} has left the game session.",
                    player=player,
                    character=character,
                    characters=await game_session_repository.characters(player_session),
                )

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
        game_session_repository = GameSessionRepository(self.surreal_manager)
        if self.game_session_category:
            db_sessions = await game_session_repository.get_all()
            db_channel_names = [session.name for session in db_sessions]

            # Delete channels that are not in the found as sessions in the database
            for channel in self.game_session_category.text_channels:
                channel_name = clean_channel_name(channel.name)
                if channel_name not in db_channel_names:
                    await delete_channel(self.bot, channel)

            # Add channels that are not in the active game channels
            for channel in self.game_session_category.text_channels:
                channel_name = clean_channel_name(channel.name)
                if channel_name not in self.active_game_channels:
                    self.active_game_channels[channel_name] = {
                        "last_active_at": datetime.now(timezone.utc),
                        "game_session": await game_session_repository.from_channel(
                            channel
                        ),
                        "history": await self._load_history(
                            await game_session_repository.from_channel(channel)
                        ),
                    }

                    self.logger.debug(
                        f"Added active game session channel: {channel.name} to active game channels"
                    )

                # Check if the channel is idle
                channel_age = (
                    datetime.now(timezone.utc)
                    - self.active_game_channels[channel_name]["last_active_at"]
                ).total_seconds()
                max_age = self.bot.game_settings.max_game_session_idle_duration * 60
                if channel_age > max_age:
                    session = await game_session_repository.from_channel(channel)
                    await self.end_game_session(session)

                    if session.name in self.active_game_channels:
                        del self.active_game_channels[session.name]
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

    async def create_game_session(
        self,
        member: discord.Member,
        open_to_all: bool = False,
        players: str | None = None,
    ) -> GameSession:
        # Create game session entry in SurrealDB and associate graph with player
        player_repository = PlayerRepository(self.surreal_manager)
        player = await player_repository.get_by_discord_id(member.id)

        characters = await player_repository.get_characters(player)
        player_character = await player_repository.get_active_character(player)

        if not characters:
            await send_dm(
                self.bot,
                member,
                "You have no characters. Create one with `/character create`",
            )
            await move_member_to_voice_channel(self.bot, member)
            return

        if not player_character:
            await send_dm(
                self.bot,
                member,
                "You have no active character. Select one with `/character use`",
            )
            await move_member_to_voice_channel(self.bot, member)
            return

        if len(self.active_game_channels) >= self.bot.game_settings.max_game_sessions:
            await send_dm(
                self.bot,
                member,
                "All game sessions are currently in use. Please try again later.",
            )
            await move_member_to_voice_channel(self.bot, member)
            return

        current_session = await player_repository.get_game_session(player)
        if current_session:
            channel_name = current_session.name
            channel = await find_channel(self.bot, channel_name)
            if not channel:
                channel = await create_text_channel(self.bot, channel_name)
                await channel.send(
                    f"Missing game session channel has been recreated {member.mention}\n"
                    "Please review the game rules and setup in the #rules channel.\n"
                    "Remember that you can use `/game help` for help with game commands.\n"
                    f"To help ensure the best experience for all players, sessions that have been idle for {self.bot.game_settings.max_game_session_idle_duration} minutes will be automatically deleted."
                )

            await move_member_to_voice_channel(self.bot, member)

            await send_dm(
                self.bot,
                member,
                f"You are already playing in a game session. Join <#{channel.id}> to continue, or end the session with `/game end`",
            )

            return

        # Generate a new channel name, check DB for duplicates and generate a new name if needed
        game_session_repository = GameSessionRepository(self.surreal_manager)

        self.logger.debug("Generating new game session name")
        channel_name = NameGenerator.generate_cyberpunk_channel_name()

        counter = 1
        while await game_session_repository.get_by_("name", channel_name):
            self.logger.debug(
                f"Duplicate game session name found, generating new name ({counter}/3)"
            )
            channel_name = NameGenerator.generate_cyberpunk_channel_name()

            counter += 1

            if counter > 3:
                self.logger.warning(
                    "Failed to generate unique game session name after 3 attempts"
                )
                await send_dm(
                    self.bot,
                    member,
                    "Failed to generate game session after 3 attempts. Please try again later.",
                )
                await self._move_member_from_join_channel(member)
                return

        game_session = GameSession(
            name=channel_name,
            channel_id=None,
            is_open=open_to_all,
            created_at=datetime.now(timezone.utc),
            last_active_at=datetime.now(timezone.utc),
        )

        await game_session_repository.upsert(game_session)
        await game_session_repository.add_player(player, game_session)
        await game_session_repository.add_character(
            player_character, game_session
        )  # TODO: Add characters to the game session

        if players:
            pass

        display_channel_name = channel_name
        if not open_to_all:
            display_channel_name = f"🔒-{channel_name}"

        channel = await create_text_channel(
            self.bot, display_channel_name, self.game_session_category
        )

        game_session.channel_id = channel.id
        await game_session_repository.upsert(game_session)

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
                use_application_commands=False,
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
            f"To help ensure the best experience for all players, sessions that have been idle for {self.bot.game_settings.max_game_session_idle_duration} minutes will be automatically deleted.",
            delete_after=60.0,
        )

        channel.slowmode_delay = self.bot.game_settings.game_channel_slowmode_delay
        self.logger.debug(
            f"Set slowmode delay to {self.bot.game_settings.game_channel_slowmode_delay} seconds"
        )
        await move_member_to_voice_channel(self.bot, member)

        self.active_game_channels[game_session.name] = {
            "last_active_at": datetime.now(timezone.utc),
            "game_session": game_session,
            "history": [],
        }
        await game_session_repository.update_last_active_at(channel)

        return game_session

    async def end_game_session(self, session: GameSession):
        """
        End the game session the player is playing in
        """
        game_session_repository = GameSessionRepository(self.surreal_manager)
        for player in await game_session_repository.players(session):
            member = self.bot.guilds[0].get_member(player.discord_id)

            if not member:
                continue

            if not member.dm_channel:
                await member.create_dm()

            await member.dm_channel.send("Game session ending...")

            await move_member_to_voice_channel(self.bot, member)

        await game_session_repository.delete(session.id)

        history_delete_query = (
            f"DELETE FROM gm_history WHERE game_session_id == '{session.id}';"
        )
        async with self.surreal_manager.get_db() as db:
            await db.query(history_delete_query)

        channel = await find_channel(self.bot, session.name)
        if channel:
            if channel.id in self.active_game_channels:
                del self.active_game_channels[session.name]
            await channel.delete()

        await member.dm_channel.send("Game session ended!")

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
                f"Created game session join channel: {game_session_join_channel}"
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

    async def _agent_run(
        self,
        game_session: GameSession,
        channel: discord.TextChannel,
        message: str,
        player: Player | None = None,
        character: Character | None = None,
        characters: dict[Character, CharacterClass] | None = None,
    ):
        game_session_repository = GameSessionRepository(self.surreal_manager)

        # If characters are not provided, get them all from the game session
        if not characters:
            characters = await game_session_repository.characters(game_session)

        agent_deps = GMAgentDependencies(
            surreal_manager=self.surreal_manager,
            game_session=game_session,
            player=player,
            action_character=character,
            characters=characters,
        )

        try:
            response = await agent.run(
                message,
                messages=self.active_game_channels[game_session.name]["history"],
                deps=agent_deps,
            )
        except Exception:
            self.logger.error(f"Failed to run agent: {traceback.format_exc()}")
            await channel.send(
                "I'm sorry, but I was unable to process your request. Please try again later.",
                delete_after=10,
            )
            return

        await self._store_history(
            game_session=game_session,
            player=player,
            characters=characters,
            message=message,
            response=response,
            action_character=character,
        )

        async for chunk in send_large_message(response.output):
            await channel.send(chunk)

    async def _init_game_sessions(self):
        self.logger.debug("Initializing game sessions")
        game_session_repository = GameSessionRepository(self.surreal_manager)

        for game_session in await game_session_repository.get_all():
            channel = await find_channel(
                self.bot, game_session.name, self.game_session_category
            )
            if not channel:
                await game_session_repository.delete(game_session.id)
                continue

            history = await self._load_history(game_session)
            self.active_game_channels[game_session.name] = {
                "last_active_at": game_session.last_active_at,
                "game_session": game_session,
                "history": history,
            }

        self.logger.debug(
            f"Loaded {len(self.active_game_channels)} active game sessions from database"
        )

    async def _store_history(
        self,
        game_session: GameSession,
        player: Player,
        characters: list[Character],
        message: str,
        response: AgentRunResult,
        action_character: Character | None = None,
    ) -> None:
        messages = json.loads(response.new_messages_json())

        self.logger.debug(
            f"Storing history for game session {game_session.id}: {messages}"
        )

        gm_history = GMHistory(
            game_session_id=str(game_session.id),
            player_id=str(player.id) if player else "",
            action_character=action_character.name if action_character else None,
            characters=[character.name for character, _ in characters],
            request=message,
            model_messages=messages,
            created_at=datetime.now(timezone.utc),
        )
        try:
            db_gm_history = await self.surreal_manager.db.create(
                "gm_history",
                gm_history.model_dump(),
            )
            gm_history = GMHistory(**db_gm_history)
        except Exception:
            self.logger.error(
                f"Failed to store long term history: {traceback.format_exc()}"
            )

        self.active_game_channels[game_session.name]["history"].extend(messages)

        # We only keep the last 20 messages in memory
        self.active_game_channels[game_session.name]["history"] = (
            self.active_game_channels[game_session.name]["history"][-20:]
        )

    async def _load_history(
        self, game_session: GameSession
    ) -> list[ModelMessagesTypeAdapter]:
        # If the game session is not found, return an empty list as there is no history to load
        if not game_session:
            return []

        self.logger.debug(f"Loading history for game session {game_session.name}")
        query = f"SELECT * FROM gm_history WHERE game_session_id == '{game_session.id}' ORDER BY created_at DESC LIMIT 20;"
        self.logger.debug("Query: %s", query)

        async with self.surreal_manager.get_db() as db:
            result = await db.query(query)

        if not result:
            return []

        history = []
        for gm_history in result:
            try:
                gm_history_model = GMHistory(**gm_history)
                history.extend(
                    ModelMessagesTypeAdapter.validate_python(gm_history_model.model_messages)
                )
            except Exception:
                self.logger.error(f"Failed to load history: {traceback.format_exc()}")
                continue

        return history


def _register_tools():
    @agent.tool
    async def fetch_npc(
        ctx: RunContext[None],
        request: RequestGenerateNPC,
    ) -> NPC:
        """When a NPC character is needed, call this tool to generate or create a new NPC for the player to interact with.

        Args:
            ctx: The context of the agent.
            request: The request to generate or create a new NPC.

        Returns:
            NPC: The generated or created NPC.
        """
        print(
            f"!!! Selecting or creating NPC: {request.name}, {request.race}, {request.background}, {request.profession}, {request.faction}, {request.location}"
        )
        return NPC.generate_npc(
            request.name,
            request.race,
            request.background,
            request.profession,
            request.faction,
            request.location,
        )

    @agent.tool
    async def get_character_credits(
        ctx: RunContext[GMAgentDependencies],
        request: RequestGetCharacterPurse,
    ) -> ResponseCharacterCredits:
        """Fetch the current state of a character's credits from the database. The default currency is the 'quill' if none other specified.

        Args:
            ctx: The context of the agent.
            request: The request to get the character's credits.

        Returns:
            ResponseCharacterCredits: The current state of the character's credits.
        """
        surreal_manager = ctx.deps.surreal_manager

        game_session_repository = GameSessionRepository(surreal_manager)
        game_session = await game_session_repository.get_by_id(ctx.deps.game_session_id)

        characters = await game_session_repository.characters(game_session)

        requesting_character = None
        for character in characters:
            if character.name == request.character_name:
                requesting_character = character
                break

        if not requesting_character:
            raise ValueError(f"Character {request.character_name} not found")

        print(f"!!! Player credits: {requesting_character.credits}")

        return ResponseCharacterCredits(
            character=requesting_character,
            credits=requesting_character.credits,
            currency=request.currency,
        )

    @agent.tool
    async def adjust_character_credits(
        ctx: RunContext[GMAgentDependencies],
        request: RequestAddCredits,
    ) -> ResponseCharacterCredits:
        """Anytime that a character's credits need to be adjusted, call this tool. This could be for purchases, sales, rewards, or other actions that affect character's wallet status.

        Args:
            ctx: The context of the agent.
            request: The request to give credits.

        Returns:
            int: The new state of the character's credits.
        """
        character = ctx.deps.character
        surreal_manager = ctx.deps.surreal_manager

        character_repository = CharacterRepository(surreal_manager)
        character = await character_repository.get_by_id(character.id)

        if not character:
            raise ValueError(f"Character {character.id} not found")

        if request.amount < 0 and character.credits + request.amount < 0:
            raise ValueError("Not enough credits")

        character.credits += request.amount
        await character_repository.update(character.id, character.model_dump())

        print(f"!!! Give credits: {request.amount}, new credits: {character.credits}")

        return character.credits

    @agent.tool
    async def add_character_quest(
        ctx: RunContext[GMAgentDependencies],
        quest: Quest,
    ) -> None:
        """
        When an NPC or other entity offers a quest to the player, call this tool to add the quest to the character.

        Args:
            ctx: The context of the agent.
            quest: The quest to add.
        """
        character = ctx.deps.character
        surreal_manager = ctx.deps.surreal_manager

        character_repository = CharacterRepository(surreal_manager)
        character = await character_repository.get_by_id(character.id)

        if not character:
            raise ValueError(f"Character {character.id} not found")

        await character_repository.add_character_quest(character, quest)

        print(f"!!! Added quest: {quest.name}")


async def _load_system_prompt(prompt_path: Path) -> AsyncGenerator[str, None]:
    logger = logging.getLogger(__name__)

    if not await aiofiles.os.path.isfile(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    async with aiofiles.open(prompt_path, mode="r") as f:
        lines = await f.readlines()

    for line in [line.strip() for line in lines]:
        if not line:
            continue

        yield line

    logger.debug(f"Loaded prompt from {prompt_path}")


def _register_system_prompts():
    @agent.system_prompt
    async def user_context(ctx: RunContext[GMAgentDependencies]) -> str:
        character_repository = CharacterRepository(ctx.deps.surreal_manager)

        if ctx.deps.action_character:
            character_class = await character_repository.get_character_class(
                ctx.deps.action_character
            )

            return f"""
            The player is playing as {ctx.deps.action_character.name}. 
            They are a {character_class.name} which has a background of ({character_class.description}). The player has the following stats:
            {ctx.deps.action_character.stats}"""

        return ""


async def setup(bot: commands.Bot) -> None:
    global model, agent
    bot.logger.info("Loading game cog...")

    model_name = os.getenv("DB_GM_MODEL_NAME", "gemma3:latest")
    base_url = os.getenv("DB_GM_BASE_URL", "http://localhost:11434/v1")

    model = OpenAIModel(
        model_name=model_name,
        provider=OpenAIProvider(base_url=base_url),
    )
    system_prompt_path = Path(
        os.getenv(
            "DB_GM_SYSTEM_PROMPT_PATH",
            os.path.dirname(__file__) + "/prompts/gm_base.md",
        )
    )

    system_prompt = []
    async for line in _load_system_prompt(system_prompt_path):
        system_prompt.append(line)

    agent = Agent(
        model=model,
        system_prompt="\n".join(system_prompt),
        deps_type=GMAgentDependencies,
        retries=3,
    )

    _register_tools()
    _register_system_prompts()

    await bot.add_cog(Game(bot=bot, surreal_manager=bot.surreal_manager))
