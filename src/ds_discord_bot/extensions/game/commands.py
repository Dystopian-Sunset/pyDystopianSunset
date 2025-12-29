"""
Game commands cog for Discord bot.

This module contains the GameCommands cog with all Discord commands and event listeners
for managing game sessions.
"""

import json
import logging
import os
import time
import traceback
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

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

from ds_common.combat import (
    apply_damage,
    apply_healing,
    consume_stamina,
    consume_tech_power,
    format_combat_status,
    format_resource_display,
    restore_resources,
    restore_stamina,
    restore_tech_power,
)
from ds_common.combat.models import DamageType
from ds_common.metrics.service import get_metrics_service
from ds_common.models.character import Character
from ds_common.models.character_class import CharacterClass
from ds_common.models.encounter import Encounter, EncounterStatus, EncounterType
from ds_common.models.game_master import (
    GMAgentDependencies,
    GMHistory,
    RequestAddCredits,
    RequestAddItem,
    RequestApplyDamage,
    RequestApplyHealing,
    RequestCheckCooldown,
    RequestConsumeResource,
    RequestCreateLocationEdge,
    RequestCreateLocationNode,
    RequestDistributeRewards,
    RequestEndEncounter,
    RequestFindAndCollectWorldItem,
    RequestGenerateNPC,
    RequestGetCharacterPurse,
    RequestGetCooldowns,
    RequestGetEquipment,
    RequestGetInventory,
    RequestGetQuests,
    RequestRemoveEquipment,
    RequestRemoveItem,
    RequestRemoveQuest,
    RequestRestoreResource,
    RequestSearchCorpse,
    RequestStartCooldown,
    RequestStartEncounter,
    RequestSwapEquipment,
    RequestUpdateCharacterLocation,
    ResponseCharacterCredits,
    ResponseCharacterLocation,
    ResponseCheckCooldown,
    ResponseCombatStatus,
    ResponseDistributeRewards,
    ResponseEncounterStatus,
    ResponseEquipment,
    ResponseFindAndCollectWorldItem,
    ResponseGetCooldowns,
    ResponseInventory,
    ResponseLocationEdge,
    ResponseLocationNode,
    ResponseQuests,
    ResponseRemoveQuest,
    ResponseSearchCorpse,
    ResponseStartCooldown,
)
from ds_common.models.game_session import GameSession
from ds_common.models.npc import NPC
from ds_common.models.player import Player
from ds_common.models.quest import Quest
from ds_common.name_generator import NameGenerator
from ds_common.repository.character import CharacterRepository
from ds_common.repository.encounter import EncounterRepository
from ds_common.repository.game_session import GameSessionRepository
from ds_common.repository.player import PlayerRepository
from ds_common.repository.quest import QuestRepository
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
from ds_discord_bot.postgres_manager import PostgresManager

class GameCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, postgres_manager: PostgresManager, agent=None):
        self.metrics = get_metrics_service()
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.bot: commands.Bot = bot
        self.postgres_manager: PostgresManager = postgres_manager
        self.game_session_category: discord.CategoryChannel | None = None
        self.game_session_join_channel: discord.VoiceChannel | None = None
        self.game_session_text_channels: list[discord.TextChannel] = []
        self.game_session_voice_channels: list[discord.VoiceChannel] = []
        self.active_game_channels: dict[str, dict] = {}

        # Initialize managers
        from .permission_manager import PermissionManager
        from .session_manager import SessionManager

        self.permission_manager = PermissionManager(bot)
        self.session_manager = SessionManager(bot, postgres_manager, self.permission_manager)

        # Initialize message processor
        from .message_processor import MessageProcessor
        
        self.message_processor = MessageProcessor(
            bot=bot,
            postgres_manager=postgres_manager,
            agent=agent,
            active_game_channels=self.active_game_channels,
        )
        
        # Initialize background tasks (will be started in on_ready)
        self.background_tasks = None

        self.check_game_sessions.start()
        self.restore_character_resources.start()

    def _get_config(self):
        """Get configuration instance."""
        from ds_common.config_bot import get_config

        return get_config()

    async def _get_location_context(self, location_id: UUID | None) -> dict[str, str | UUID | None]:
        """
        Get location context including parent locations and region information.

        Args:
            location_id: Location node ID

        Returns:
            Dictionary with location context: {
                'location_id': UUID,
                'location_name': str,
                'location_type': str,
                'parent_location_id': UUID | None,
                'parent_location_name': str | None,
                'region_name': str | None,
                'city': str | None,
                'district': str | None,
                'sector': str | None,
            }
        """
        from ds_discord_bot.extensions.game.context_builder import ContextBuilder

        context_builder = ContextBuilder(self.postgres_manager)
        return await context_builder.get_location_context(location_id)

    def _create_redis_client(self, db_number: int):
        """
        Create a Redis client for the specified database number.

        Args:
            db_number: Redis database number (0 for prompt analyzer, 1 for memory)

        Returns:
            Redis client or None if Redis is not available
        """
        try:
            import redis.asyncio as redis

            config = self._get_config()
            redis_url = config.redis_url
            # Create connection with specific database number
            # Note: We don't await here as Redis connection is typically lazy
            return redis.from_url(redis_url, db=db_number)
        except Exception as e:
            self.logger.debug(f"Redis not available for db {db_number}: {e}")
            return None

    @commands.Cog.listener()
    async def on_ready(self):
        self.game_session_category = await find_category(
            self.bot, self._get_config().game_session_category_name
        )
        self.game_session_join_channel = await find_channel(
            self.bot,
            self._get_config().game_session_join_channel_name,
            self.game_session_category,
        )
        await self._init_game_sessions()

        # Notify active sessions that the game is back online
        await self._notify_active_sessions_startup()

        # Initialize game time and fast-forward if needed
        try:
            from ds_common.memory.game_time_service import GameTimeService

            game_time_service = GameTimeService(self.postgres_manager)
            await game_time_service.get_current_game_time()  # This initializes if needed
            # Fast-forward game time based on elapsed real-world time since last shutdown
            await game_time_service.fast_forward_on_startup()
            self.logger.info("Game time initialized and fast-forwarded")
        except Exception as e:
            self.logger.warning(f"Failed to initialize game time: {e}")

        # Initialize and start background tasks
        try:
            from ds_common.memory.background_tasks import BackgroundTasks

            self.background_tasks = BackgroundTasks(self.postgres_manager)
            await self.background_tasks.start()
            self.logger.info("Background tasks started (game time, events, calendar)")
        except Exception as e:
            # Don't fail if background tasks can't start
            self.logger.warning(f"Failed to start background tasks: {e}")

        self.logger.info("Game cog loaded")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.TextChannel):
        self.logger.debug(f"Guild channel created: {channel}")

        game_session_repository = GameSessionRepository(self.postgres_manager)

        if channel.category == self.game_session_category:
            self.logger.debug(f"Game session channel created: {channel}")
            self.game_session_text_channels.append(channel)

            channel_name = clean_channel_name(channel.name)
            if channel_name not in self.active_game_channels:
                game_session = await game_session_repository.from_channel(channel)
                
                if not game_session:
                    self.logger.warning(
                        f"Game session not found for channel {channel.name}. "
                        f"Skipping initialization."
                    )
                    return
                
                self.logger.debug(
                    f"Adding missing game session channel to active game channels: {channel.name}"
                )
                self.active_game_channels[channel_name] = {
                    "last_active_at": datetime.now(UTC),
                    "game_session": game_session,
                    "history": list(await self.message_processor.load_history(game_session)),
                }

                async with channel.typing():
                    characters = await game_session_repository.characters(game_session)
                    character_classes = [
                        f"{character[0].name} ({character[1].name})" for character in characters
                    ]
                    await self.message_processor.agent_run(
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

        # Skip DMs - game sessions only work in server channels
        if isinstance(message.channel, discord.DMChannel):
            return

        game_session_repository = GameSessionRepository(self.postgres_manager)

        channel_name = clean_channel_name(message.channel.name)
        if channel_name in self.active_game_channels:
            self.logger.debug(f"Message in active game session channel: {message.channel.name}")

            player_repository = PlayerRepository(self.postgres_manager)
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
                self.logger.debug(f"Command in active game session channel: {message.channel.name}")

            else:
                # Check if message requires GM involvement using conversation classifier
                should_process = await self.message_processor.should_process_message(message.content)

                if not should_process:
                    self.logger.debug(
                        f"Skipping GM processing for player-to-player chat: {message.content[:50]}..."
                    )
                    # Update last active time but don't process the message
                    self.active_game_channels[game_session.name]["last_active_at"] = datetime.now(
                        UTC
                    )
                    await game_session_repository.update_last_active_at(message.channel)
                    return

                async with message.channel.typing():
                    await self.message_processor.agent_run(
                        game_session=game_session,
                        channel=message.channel,
                        message=message.content,
                        player=player,
                        character=character,
                        characters=await game_session_repository.characters(game_session),
                    )

            self.active_game_channels[game_session.name]["last_active_at"] = datetime.now(UTC)
            await game_session_repository.update_last_active_at(message.channel)

        else:
            self.logger.warning(
                f"Message in non-active game session channel: {message.channel.name}"
            )

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Prevent message edits in game session channels."""
        if after.author.bot:
            return

        # Skip DMs - game sessions only work in server channels
        if isinstance(after.channel, discord.DMChannel):
            return

        # Check if this is a game session channel
        channel_name = clean_channel_name(after.channel.name)
        if channel_name in self.active_game_channels:
            # Delete the edited message and notify the user
            try:
                await after.delete()
                # Send a warning message that gets auto-deleted
                warning = await after.channel.send(
                    f"{after.author.mention}, message editing is not allowed in game sessions. "
                    "Please send a new message instead.",
                    delete_after=10.0,
                )
                self.logger.info(
                    f"Deleted edited message from {after.author} in game session channel {after.channel.name}"
                )
            except discord.Forbidden:
                self.logger.warning(
                    f"Could not delete edited message in game session channel {after.channel.name} - missing permissions"
                )
            except discord.NotFound:
                # Message was already deleted, ignore
                pass
            except Exception as e:
                self.logger.error(f"Error handling message edit: {e}")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,  # noqa: ARG002
        after: discord.VoiceState,
    ):
        if self.game_session_join_channel and after.channel == self.game_session_join_channel:
            self.logger.debug(f"Member {member} joined game session channel {after.channel}")

            await self.create_game_session(member)

    async def cog_unload(self) -> None:
        """Cleanup when cog is unloaded."""
        # Send shutdown message to active game sessions
        await self._notify_active_sessions_shutdown()

        # Persist game time on shutdown
        try:
            from ds_common.memory.game_time_service import GameTimeService

            game_time_service = GameTimeService(self.postgres_manager)
            await game_time_service.persist_game_time_on_shutdown()
        except Exception as e:
            self.logger.error(f"Failed to persist game time on shutdown: {e}")

        # Stop background tasks
        if self.background_tasks:
            try:
                await self.background_tasks.stop()
                self.logger.info("Background tasks stopped")
            except Exception as e:
                self.logger.warning(f"Error stopping background tasks: {e}")

        # Stop periodic tasks
        self.check_game_sessions.cancel()
        self.restore_character_resources.cancel()

        self.logger.info("Game cog unloaded")

    game = app_commands.Group(name="game", description="Game commands")

    @game.command(name="start", description="Start a new game")
    @app_commands.describe(
        open_to_all="Open to all players",
        p1="First player to invite (optional)",
        p2="Second player to invite (optional)",
        p3="Third player to invite (optional)",
        p4="Fourth player to invite (optional)",
    )
    async def start(
        self,
        interaction: discord.Interaction,
        open_to_all: bool = False,
        p1: discord.Member | None = None,
        p2: discord.Member | None = None,
        p3: discord.Member | None = None,
        p4: discord.Member | None = None,
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Log raw interaction data for debugging
        self.logger.debug(
            f"Raw interaction data - command: {interaction.command}, "
            f"options: {interaction.data.get('options', []) if hasattr(interaction, 'data') else 'N/A'}"
        )

        # Collect all non-None user parameters into a list
        users = [u for u in [p1, p2, p3, p4] if u is not None]
        self.logger.info(
            f"Command handler: Collected users list. "
            f"p1={p1}, p2={p2}, p3={p3}, p4={p4}, "
            f"users={users}, users_len={len(users)}, "
            f"user_ids={[u.id for u in users] if users else []}"
        )
        if users:
            self.logger.info(f"Inviting users: {[u.id for u in users]}")

        session: GameSession | None = None
        try:
            self.logger.info(
                f"Calling create_game_session with users={users}, users_len={len(users) if users else 0}"
            )
            session = await self.create_game_session(
                interaction.user, open_to_all=open_to_all, users=users
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

        player_repository = PlayerRepository(self.postgres_manager)
        player = await player_repository.get_by_discord_id(interaction.user.id)

        game_session_repository = GameSessionRepository(self.postgres_manager)
        game_session = await game_session_repository.from_channel(interaction.channel)
        if not game_session:
            await interaction.followup.send("Game session not found", ephemeral=True)
            return

        # Only the session creator can open/close the session
        if not await self._is_session_creator(player, game_session):
            await interaction.followup.send(
                "Only the session creator can open or close the game session.", ephemeral=True
            )
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

        player_repository = PlayerRepository(self.postgres_manager)
        player = await player_repository.get_by_discord_id(interaction.user.id)

        game_session_repository = GameSessionRepository(self.postgres_manager)
        game_session = await game_session_repository.from_channel(interaction.channel)
        if not game_session:
            await interaction.followup.send("Game session not found", ephemeral=True)
            return

        # Only the session creator can open/close the session
        if not await self._is_session_creator(player, game_session):
            await interaction.followup.send(
                "Only the session creator can open or close the game session.", ephemeral=True
            )
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

        player_repository = PlayerRepository(self.postgres_manager)
        player = await player_repository.get_by_discord_id(interaction.user.id)

        session = await player_repository.get_game_session(player)
        if not session:
            await interaction.followup.send("You are not playing in a game", ephemeral=True)
            return

        # Only the session creator can end the session
        if not await self._is_session_creator(player, session):
            await interaction.followup.send(
                "Only the session creator can end the game session.", ephemeral=True
            )
            return

        await interaction.followup.send("Ending game session", ephemeral=True)

        await self.end_game_session(session)

    @game.command(name="join", description="Join a game session")
    @app_commands.describe(
        game_name="Game session name",
    )
    async def join(self, interaction: discord.Interaction, game_name: str):
        await interaction.response.defer(ephemeral=True, thinking=True)

        game_session_repository = GameSessionRepository(self.postgres_manager)
        player_repository = PlayerRepository(self.postgres_manager)
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
            await interaction.followup.send("You are already playing in a game", ephemeral=True)
            return

        game_session = await game_session_repository.get_by_field("name", game_name)
        if not game_session:
            await interaction.followup.send("Game session not found", ephemeral=True)
            return

        if game_session.is_open:
            # Check session capacity before allowing join
            current_players = await game_session_repository.players(game_session)
            if len(current_players) >= game_session.max_players:
                await interaction.followup.send(
                    f"The game session is full (max {game_session.max_players} players). "
                    f"Current players: {len(current_players)}/{game_session.max_players}",
                    ephemeral=True,
                )
                return

            await game_session_repository.add_player(player, game_session)
            await game_session_repository.add_character(player_character, game_session)
            self.metrics.record_game_session("player_joined")

            # Apply catch-up restoration when player joins/returns to session
            character_repository = CharacterRepository(self.postgres_manager)
            player_character = await character_repository.catch_up_restoration_on_session_start(
                player_character
            )

            channel = await find_channel(self.bot, game_session.name)
            if not channel:
                self.logger.warning(f"Channel not found for game session: {game_session.name}")
                return

            # Check if player has citizen role - required to join sessions
            if not await self._has_player_role(interaction.user):
                config = self._get_config()
                rules_channel_name = config.game_rules_channel_name
                rules_channel_mention = f"#{rules_channel_name}" if rules_channel_name else "the rules channel"
                
                await interaction.followup.send(
                    f"⚠️ **Cannot join the game session.**\n\n"
                    f"You do not have the **citizen** role and cannot join game sessions.\n\n"
                    f"**To get the citizen role:**\n"
                    f"1. Go to {rules_channel_mention}\n"
                    f"2. Accept the server rules by reacting to the required messages\n"
                    f"3. Once you have the citizen role, you can join game sessions\n\n"
                    f"The citizen role is required to participate in game sessions for security and rule compliance.",
                    ephemeral=True
                )
                return

            # Add player to session role
            await self._add_player_to_session_role(interaction.user, game_session)

            character_repository = CharacterRepository(self.postgres_manager)
            character_class = await character_repository.get_character_class(player_character)
            async with channel.typing():
                await self.message_processor.agent_run(
                    game_session=game_session,
                    channel=channel,
                    message=f"Introduce {player_character.name} ({character_class.name}) to the party. Maintain theme and lore of the game session.",
                    player=player,
                    character=player_character,
                    characters=await game_session_repository.characters(game_session),
                )

            # Send welcome DM to the player who joined
            try:
                channel_link = f"https://discord.com/channels/{channel.guild.id}/{channel.id}"
                await send_dm(
                    self.bot,
                    interaction.user,
                    f"🎮 **Welcome to the game session!**\n\n"
                    f"You've joined **{game_session.name}**.\n\n"
                    f"**Your character:** {player_character.name} ({character_class.name})\n\n"
                    f"Join the session here: <#{channel.id}>\n"
                    f"Or use this link: {channel_link}\n\n"
                    f"See you in the game! 👋",
                )
            except Exception as e:
                self.logger.warning(f"Failed to send DM to {interaction.user.display_name}: {e}")

            await interaction.followup.send("You have joined the game session", ephemeral=True)

        else:
            await interaction.followup.send(
                "Game session is not open to all players", ephemeral=True
            )
            return

    async def _is_session_creator(self, player: Player, game_session: GameSession) -> bool:
        """
        Check if a player is the creator of a game session.
        The creator is the first player added to the session.

        Args:
            player: Player to check
            game_session: Game session to check

        Returns:
            True if player is the session creator
        """
        return await self.session_manager.is_session_creator(player, game_session)

    async def _has_gm_role(self, member: discord.Member | discord.User) -> bool:
        """
        Check if a member has the GM role.

        Args:
            member: Discord member or user to check

        Returns:
            True if the member has the GM role, False otherwise
        """
        return await self.permission_manager.has_gm_role(member)

    async def _has_player_role(self, member: discord.Member | discord.User) -> bool:
        """
        Check if a member has the player role.

        Args:
            member: Discord member or user to check

        Returns:
            True if the member has the player role, False otherwise
        """
        return await self.permission_manager.has_player_role(member)

    async def _create_session_role(self, game_session: GameSession) -> discord.Role:
        """Delegate to PermissionManager."""
        return await self.permission_manager.create_session_role(game_session)

    async def _get_session_role(self, game_session: GameSession) -> discord.Role | None:
        """Delegate to PermissionManager."""
        return await self.permission_manager.get_session_role(game_session)

    async def _delete_session_role(self, game_session: GameSession) -> None:
        """Delegate to PermissionManager."""
        await self.permission_manager.delete_session_role(game_session)
        """
        Delete the Discord role for a game session.
        Critical for maintaining 1:1 relationship.

        Args:
            game_session: The game session whose role should be deleted
        """
        role = await self._get_session_role(game_session)
        if not role:
            self.logger.debug(
                f"Role '{game_session.name}' not found when deleting session {game_session.id}. "
                f"It may have already been deleted."
            )
            return

        try:
            await role.delete(reason=f"Game session {game_session.id} ended")
            self.logger.info(f"Deleted session role '{role.name}' for session {game_session.id}")
        except discord.Forbidden:
            self.logger.error(
                f"Bot lacks permission to delete role '{role.name}' for session {game_session.id}. "
                f"Bot needs 'Manage Roles' permission."
            )
        except discord.NotFound:
            self.logger.debug(
                f"Role '{role.name}' was already deleted for session {game_session.id}"
            )
        except Exception as e:
            self.logger.error(
                f"Failed to delete role '{role.name}' for session {game_session.id}: {e}",
                exc_info=True
            )

    async def _add_player_to_session_role(
        self, member: discord.Member, game_session: GameSession
    ) -> None:
        """Delegate to PermissionManager."""
        await self.permission_manager.add_player_to_session_role(member, game_session)

    async def _remove_player_from_session_role(
        self, member: discord.Member, game_session: GameSession
    ) -> None:
        """Delegate to PermissionManager."""
        await self.permission_manager.remove_player_from_session_role(member, game_session)

    async def _validate_session_role_sync(self, game_session: GameSession) -> bool:
        """
        Validate that session and role are synchronized.
        Checks role exists, all players have the role, and no orphaned role members.

        Args:
            game_session: The game session to validate

        Returns:
            True if synchronized, False if discrepancies found
        """
        game_session_repository = GameSessionRepository(self.postgres_manager)
        player_repository = PlayerRepository(self.postgres_manager)

        # Check if role exists
        role = await self._get_session_role(game_session)
        if not role:
            self.logger.warning(
                f"Session {game_session.id} ({game_session.name}) has no matching role"
            )
            return False

        # Get all players in session
        session_players = await game_session_repository.players(game_session)
        guild = self.bot.guilds[0] if self.bot.guilds else None
        if not guild:
            return False

        synchronized = True

        # Check all players in session have the role
        for player in session_players:
            member = guild.get_member(player.discord_id)
            if not member:
                continue

            # Skip GM users
            if await self._has_gm_role(member):
                continue

            if role not in member.roles:
                self.logger.warning(
                    f"Player {player.discord_id} is in session {game_session.name} but missing role"
                )
                synchronized = False
                # Auto-fix: add role
                await self._add_player_to_session_role(member, game_session)

        # Check for players with role but not in session (should not happen due to 1 session per player)
        for member in guild.members:
            if role in member.roles:
                # Skip GM users
                if await self._has_gm_role(member):
                    continue

                # Check if member is in this session
                player = await player_repository.get_by_discord_id(member.id)
                if player:
                    player_session = await player_repository.get_game_session(player)
                    if player_session and player_session.id != game_session.id:
                        # Player has this role but is in a different session - this is an error
                        self.logger.warning(
                            f"Player {member.display_name} has role '{role.name}' but is in different session '{player_session.name}'"
                        )
                        synchronized = False
                    elif not player_session:
                        # Player has role but not in any session - remove role
                        self.logger.warning(
                            f"Player {member.display_name} has role '{role.name}' but not in any session - removing role"
                        )
                        synchronized = False
                        await self._remove_player_from_session_role(member, game_session)

        return synchronized

    async def _grant_channel_permissions(
        self,
        channel: discord.TextChannel,
        member: discord.Member,
        game_session_name: str,
    ) -> None:
        """
        Grant full channel permissions to a member for a game session.
        Individual member permissions override role permissions.

        Args:
            channel: The Discord channel to set permissions on
            member: The member to grant permissions to
            game_session_name: Name of the game session (for logging)
        """
        try:
            # Get current overwrites to preserve existing permissions
            current_overwrites = channel.overwrites.copy()

            # Create/update the member's permission overwrite
            # IMPORTANT: Set all permissions explicitly, including ones that might be denied by role
            member_overwrite = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_messages=True,
                read_message_history=True,
                add_reactions=True,
                use_application_commands=True,
                create_instant_invite=False,  # Explicitly set to False to override role
            )
            current_overwrites[member] = member_overwrite

            # Update channel with all overwrites at once
            await channel.edit(overwrites=current_overwrites)

            # Verify permissions were actually set
            member_overwrite_check = channel.overwrites_for(member)
            self.logger.info(
                f"Set channel permissions for {member.display_name} (ID: {member.id}) "
                f"in session {game_session_name} using channel.edit(). "
                f"Verified: view_channel={member_overwrite_check.view_channel}, "
                f"send_messages={member_overwrite_check.send_messages}"
            )

            # If permissions weren't set correctly, log a warning
            if member_overwrite_check.view_channel is None or member_overwrite_check.send_messages is None:
                self.logger.warning(
                    f"Permissions may not have been set correctly for {member.display_name}. "
                    f"view_channel={member_overwrite_check.view_channel}, "
                    f"send_messages={member_overwrite_check.send_messages}"
                )
        except discord.Forbidden:
            self.logger.error(
                f"Bot lacks permission to edit channel permissions for {member.display_name}. "
                f"Bot needs 'Manage Channels' permission."
            )
            raise
        except Exception as e:
            self.logger.error(
                f"Failed to set channel permissions for {member.display_name}: {e}",
                exc_info=True
            )
            # Don't raise - continue even if permissions fail (they might still work)
            # The user can manually set permissions if needed

    async def _revoke_channel_content_access(
        self,
        channel: discord.TextChannel,
        member: discord.Member | discord.User,
        game_session_name: str,
    ) -> None:
        """
        Revoke channel content access for a member while allowing them to see the channel name.
        This is used when players leave or are removed from a session.

        Args:
            channel: The Discord channel to set permissions on
            member: The member to revoke permissions for
            game_session_name: Name of the game session (for logging)
        """
        try:
            # Ensure we have a Member object
            if isinstance(member, discord.User) and not isinstance(member, discord.Member):
                guild = channel.guild
                member = guild.get_member(member.id)
                if not member:
                    self.logger.warning(f"Could not get member object for {member.id}")
                    return

            # Set permissions: can see channel name but not content
            await channel.set_permissions(
                member,
                view_channel=True,  # Can see channel name
                create_instant_invite=False,
                send_messages=False,  # Can't send messages
                read_messages=False,  # Can't read content
                read_message_history=False,  # Can't read history
                add_reactions=False,
                use_application_commands=False,
            )

            self.logger.info(
                f"Revoked channel content access for {member.display_name} (ID: {member.id}) "
                f"in session {game_session_name}. They can see the channel name but not content."
            )
        except discord.Forbidden:
            self.logger.error(
                f"Bot lacks permission to edit channel permissions for {member.display_name}. "
                f"Bot needs 'Manage Channels' permission."
            )
        except Exception as e:
            self.logger.error(
                f"Failed to revoke channel permissions for {member.display_name}: {e}",
                exc_info=True
            )

    async def _add_users_to_session_at_start(
        self,
        users: list[discord.User],
        creator: discord.Member,
        game_session: GameSession,
        channel: discord.TextChannel,
        player_repository: PlayerRepository,
        game_session_repository: GameSessionRepository,
    ) -> None:
        """
        Add multiple users to a game session at creation time.
        Handles validation, player creation, character checks, and permissions.

        Args:
            users: List of Discord users to add
            creator: The session creator (to skip if in list and handle errors)
            game_session: The game session to add users to
            channel: The game session channel
            player_repository: Player repository instance
            game_session_repository: Game session repository instance
        """
        self.logger.info(
            f"_add_users_to_session_at_start called for session '{game_session.name}' with {len(users) if users else 0} user(s)"
        )
        
        # Refresh channel to ensure we have the latest state with all permissions
        # This is important because the channel was just created and Discord may not have
        # fully propagated all permission changes yet
        channel = await find_channel(self.bot, game_session.name)
        if not channel:
            self.logger.error(
                f"Channel not found for game session {game_session.name} when adding users. "
                f"This should not happen as the channel was just created."
            )
            return
        
        character_repository = CharacterRepository(self.postgres_manager)
        guild = creator.guild
        added_users = []
        errors = []
        failed_players = []  # Track players who fail citizen role check

        # Remove duplicates and the creator from the list
        seen_ids = {creator.id}
        unique_users = []
        for user in users:
            if user.id not in seen_ids:
                unique_users.append(user)
                seen_ids.add(user.id)
            elif user.id == creator.id:
                self.logger.debug(f"Skipping creator {creator.id} from user list")

        self.logger.info(
            f"Processing {len(unique_users)} invited user(s) for session '{game_session.name}': "
            f"{[u.display_name if hasattr(u, 'display_name') else str(u) for u in unique_users]}"
        )
        
        for user in unique_users:
            try:
                self.logger.debug(f"Processing user {user} (ID: {user.id}) for session '{game_session.name}'")
                # Check if user is in the server
                member = guild.get_member(user.id)
                if not member:
                    self.logger.warning(f"User {user} (ID: {user.id}) is not in the server")
                    errors.append(f"{user} is not in the server")
                    continue

                # Skip GM users - they're already in every game session
                if await self._has_gm_role(member):
                    self.logger.debug(f"Skipping GM user {member.display_name} from user list")
                    continue

                # Check if user has citizen role - required to join sessions
                if not await self._has_player_role(member):
                    failed_players.append((user, member))
                    self.logger.warning(
                        f"User {member.display_name} (ID: {member.id}) does not have citizen role - cannot add to session"
                    )
                    errors.append(f"{member.mention} does not have the citizen role (must accept server rules first)")
                    continue

                # Get or create the player
                target_player = await player_repository.get_by_discord_id(member.id)
                if not target_player:
                    target_player = Player.from_member(member)
                    target_player = await player_repository.upsert(target_player)
                    self.logger.info(f"Created new player record for {member.display_name}")

                # Check if player has an active character
                target_character = await player_repository.get_active_character(target_player)
                if not target_character:
                    errors.append(f"{member.mention} needs to create a character first")
                    continue

                # Check if player is already in a game session
                # NOTE: This should not happen if validation in create_game_session worked correctly,
                # but we check here as a safety measure in case something changed
                target_session = await player_repository.get_game_session(target_player)
                already_in_this_session = False
                if target_session:
                    if target_session.id == game_session.id:
                        # User is already in this session - they were added in create_game_session
                        # We still need to set permissions, but skip database operations
                        self.logger.debug(
                            f"{member.display_name} is already in this game session (added during creation), "
                            f"skipping database operations but will set permissions"
                        )
                        already_in_this_session = True
                    else:
                        # User is in a different session - this is an error state
                        self.logger.warning(
                            f"{member.display_name} is already in another game session '{target_session.name}'. "
                            f"This should have been caught during session creation validation."
                        )
                        errors.append(f"{member.mention} is already in another game session '{target_session.name}'")
                        continue

                # Only do database operations if user wasn't already added
                if not already_in_this_session:
                    # Check session capacity
                    current_players = await game_session_repository.players(game_session)
                    if len(current_players) >= game_session.max_players:
                        errors.append(
                            f"Session is full (max {game_session.max_players} players). "
                            f"Cannot add {member.mention}"
                        )
                        break  # Stop trying to add more users

                    # Add player to session
                    await game_session_repository.add_player(target_player, game_session)
                    await game_session_repository.add_character(target_character, game_session)

                    # Apply catch-up restoration
                    target_character = await character_repository.catch_up_restoration_on_session_start(
                        target_character
                    )
                else:
                    # User was already added in create_game_session - ensure we have their character
                    # (it should already be loaded from line 894, but verify)
                    if not target_character:
                        target_character = await player_repository.get_active_character(target_player)
                        if not target_character:
                            errors.append(f"{member.mention} needs to create a character first")
                            continue

                # Add player to session role - CRITICAL: This must run for ALL users, including those
                # already added during session creation, otherwise they won't be able to speak
                self.logger.info(
                    f"Attempting to add {member.display_name} (ID: {member.id}) to session role for '{game_session.name}'"
                )
                try:
                    await self._add_player_to_session_role(member, game_session)
                    self.logger.info(
                        f"Completed role assignment attempt for {member.display_name} to session '{game_session.name}'"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Exception during role assignment for {member.display_name} to session '{game_session.name}': {e}",
                        exc_info=True
                    )
                    # Don't re-raise - continue with user addition even if role assignment fails
                    # The sync task will fix it later

                # Get character class (needed for both introduction and DM)
                character_class = await character_repository.get_character_class(target_character)

                # Only introduce characters individually if they weren't part of the initial session creation
                # The initial scene (from on_guild_channel_create) already introduces all characters at once
                # Individual introductions are only needed when players join an existing session
                if not already_in_this_session:
                    # Introduce the character to the party
                    async with channel.typing():
                        await self.message_processor.agent_run(
                            game_session=game_session,
                            channel=channel,
                            message=f"Introduce {target_character.name} ({character_class.name}) to the party. Maintain theme and lore of the game session.",
                            player=target_player,
                            character=target_character,
                            characters=await game_session_repository.characters(game_session),
                        )

                # Send welcome DM
                try:
                    channel_link = f"https://discord.com/channels/{channel.guild.id}/{channel.id}"
                    await send_dm(
                        self.bot,
                        member,
                        f"🎮 **Welcome to the game session!**\n\n"
                        f"You've been invited to join **{game_session.name}** by {creator.mention}.\n\n"
                        f"**Your character:** {target_character.name} ({character_class.name})\n\n"
                        f"Join the session here: <#{channel.id}>\n"
                        f"Or use this link: {channel_link}\n\n"
                        f"See you in the game! 👋",
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to send DM to {member.display_name}: {e}")

                added_users.append(member)
                self.logger.info(f"Successfully added {member.display_name} to game session")

            except Exception as e:
                self.logger.error(f"Error adding user {user} to session: {e}", exc_info=True)
                errors.append(f"Failed to add {user}: {e!s}")

        # Send warnings for players who failed citizen role check
        if failed_players:
            config = self._get_config()
            rules_channel_name = config.game_rules_channel_name
            rules_channel_mention = f"#{rules_channel_name}" if rules_channel_name else "the rules channel"
            
            # Build warning message for creator
            failed_mentions = [m.mention for _, m in failed_players]
            warning_message = (
                f"⚠️ **Some players could not be added to the session:**\n\n"
                f"The following players do not have the **citizen** role and cannot join game sessions:\n"
                f"{', '.join(failed_mentions)}\n\n"
                f"**To fix this:**\n"
                f"1. Ask them to accept the server rules in {rules_channel_mention}\n"
                f"2. Once they have the citizen role, you can add them to the session using `/game add`\n\n"
                f"Players need the citizen role to participate in game sessions for security and rule compliance."
            )
            try:
                await send_dm(self.bot, creator, warning_message)
            except Exception as e:
                self.logger.warning(f"Failed to send citizen role warning to session creator: {e}")
            
            # Send warnings to failed players
            for user, member_user in failed_players:
                player_warning = (
                    f"⚠️ **Cannot Join Game Session**\n\n"
                    f"You were invited to join **{game_session.name}** by {creator.mention}, but you don't have the **citizen** role.\n\n"
                    f"**To get the citizen role:**\n"
                    f"1. Go to {rules_channel_mention}\n"
                    f"2. Accept the server rules by reacting to the required messages\n"
                    f"3. Once you have the citizen role, ask {creator.mention} to invite you again using `/game add`\n\n"
                    f"The citizen role is required to participate in game sessions for security and rule compliance."
                )
                try:
                    await send_dm(self.bot, member_user, player_warning)
                except Exception as e:
                    self.logger.warning(f"Failed to send citizen role warning to {member_user.display_name}: {e}")

        # Log results
        if added_users:
            self.logger.info(
                f"Added {len(added_users)} user(s) to game session: {[u.display_name for u in added_users]}"
            )
        if errors:
            self.logger.warning(f"Errors while adding users: {errors}")

    @game.command(name="add", description="Add a player to your game session")
    @app_commands.describe(
        player="User to add",
    )
    async def add_player(self, interaction: discord.Interaction, player: discord.User):
        """Add a specific player to the current game session without opening it to everyone."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        game_session_repository = GameSessionRepository(self.postgres_manager)
        player_repository = PlayerRepository(self.postgres_manager)

        # Check if the command user is in a game session
        inviter = await player_repository.get_by_discord_id(interaction.user.id)
        if not inviter:
            await interaction.followup.send(
                "You are not registered as a player. Please use `/character create` first.",
                ephemeral=True,
            )
            return

        inviter_session = await player_repository.get_game_session(inviter)
        if not inviter_session:
            await interaction.followup.send(
                "You are not currently in a game session. Start one with `/game start` first.",
                ephemeral=True,
            )
            return

        # Check if user is the session creator
        if not await self._is_session_creator(inviter, inviter_session):
            await interaction.followup.send(
                "Only the game session creator can add players. Use `/game open` to make the session open to all players.",
                ephemeral=True,
            )
            return

        # Check if trying to add themselves
        if player.id == interaction.user.id:
            await interaction.followup.send(
                "You cannot add yourself to the session.", ephemeral=True
            )
            return

        # Check if the user is actually a member of the server
        member = interaction.guild.get_member(player.id)
        
        if not member:
            # User is not in the server - create an invite and send it to the inviter
            try:
                # Get the game channel to create an invite
                channel = await find_channel(self.bot, inviter_session.name)
                if channel:
                    # Create a temporary invite (expires in 7 days, max 1 use)
                    invite = await channel.create_invite(
                        max_age=604800,  # 7 days in seconds
                        max_uses=1,
                        unique=True,
                        reason=f"Invite for {player} to join game session {inviter_session.name}",
                    )
                    invite_message = (
                        f"⚠️ **{player} is not in the server**\n\n"
                        f"You tried to add them to your game session **{inviter_session.name}**, "
                        f"but they need to join the server first.\n\n"
                        f"**Send them this invite link:**\n"
                        f"{invite.url}\n\n"
                        f"Once they join the server, you can add them again with `/game add`."
                    )
                else:
                    # Fallback: create a server invite if channel not found
                    invite = await interaction.guild.text_channels[0].create_invite(
                        max_age=604800,
                        max_uses=1,
                        unique=True,
                        reason=f"Server invite for {player}",
                    )
                    invite_message = (
                        f"⚠️ **{player} is not in the server**\n\n"
                        f"You tried to add them to your game session **{inviter_session.name}**, "
                        f"but they need to join the server first.\n\n"
                        f"**Send them this server invite link:**\n"
                        f"{invite.url}\n\n"
                        f"Once they join the server, you can add them to your game session with `/game add`."
                    )

                # Send DM to the inviter with the invite link
                await send_dm(
                    self.bot,
                    interaction.user,
                    invite_message,
                )

                await interaction.followup.send(
                    f"⚠️ {player} is not in the server. I've sent you a DM with an invite link you can share with them.",
                    ephemeral=True,
                )
            except Exception as e:
                self.logger.error(f"Failed to create invite: {e}")
                # Provide a copy-paste message for the creator
                fallback_message = (
                    f"⚠️ **{player} is not in the server**\n\n"
                    f"I couldn't automatically create an invite, but you can invite them manually:\n\n"
                    f"**Option 1:** Right-click the server name → 'Invite People' → Create invite → Send to {player}\n\n"
                    f"**Option 2:** Copy this message and send it to {player}:\n"
                    f"```\n"
                    f"Hey! I'd like to invite you to join our game session '{inviter_session.name}' "
                    f"on the {interaction.guild.name} Discord server. "
                    f"Can you join the server? Once you're in, I can add you to the game!\n"
                    f"```\n\n"
                    f"After they join, use `/game add` again to add them to your session."
                )

                # Try to send DM with fallback message
                try:
                    await send_dm(
                        self.bot,
                        interaction.user,
                        fallback_message,
                    )
                    await interaction.followup.send(
                        f"⚠️ {player} is not in the server. I couldn't create an invite automatically, "
                        f"but I've sent you a DM with instructions you can copy-paste.",
                        ephemeral=True,
                    )
                except Exception as dm_error:
                    # If DM also fails, send the message in the interaction response
                    self.logger.error(f"Failed to send DM: {dm_error}")
                    await interaction.followup.send(
                        fallback_message,
                        ephemeral=True,
                    )
            return

        # Skip GM users - they're already in every game session
        if await self._has_gm_role(member):
            await interaction.followup.send(
                f"{player.mention} is a GM and is already in all game sessions. Skipping.",
                ephemeral=True,
            )
            return

        # Check if player has citizen role - required to join sessions
        if not await self._has_player_role(member):
            config = self._get_config()
            rules_channel_name = config.game_rules_channel_name
            rules_channel_mention = f"#{rules_channel_name}" if rules_channel_name else "the rules channel"
            
            # Send warning to inviter
            await interaction.followup.send(
                f"⚠️ **Cannot add {player.mention} to the session.**\n\n"
                f"They do not have the **citizen** role and cannot join game sessions.\n\n"
                f"**To fix this:**\n"
                f"1. Ask them to accept the server rules in {rules_channel_mention}\n"
                f"2. Once they have the citizen role, you can add them using `/game add` again\n\n"
                f"Players need the citizen role to participate in game sessions for security and rule compliance.",
                ephemeral=True
            )
            
            # Send warning to the player
            player_warning = (
                f"⚠️ **Cannot Join Game Session**\n\n"
                f"You were invited to join **{inviter_session.name}** by {interaction.user.mention}, but you don't have the **citizen** role.\n\n"
                f"**To get the citizen role:**\n"
                f"1. Go to {rules_channel_mention}\n"
                f"2. Accept the server rules by reacting to the required messages\n"
                f"3. Once you have the citizen role, ask {interaction.user.mention} to invite you again using `/game add`\n\n"
                f"The citizen role is required to participate in game sessions for security and rule compliance."
            )
            try:
                await send_dm(self.bot, member, player_warning)
            except Exception as e:
                self.logger.warning(f"Failed to send citizen role warning to {member.display_name}: {e}")
            
            return

        # Get or create the target player (now we know member exists)
        target_player = await player_repository.get_by_discord_id(member.id)
        if not target_player:
            # Create player if they don't exist
            target_player = Player.from_member(member)
            target_player = await player_repository.upsert(target_player)
            self.logger.info(f"Created new player record for {member.display_name}")

        # Check if target player already has a character
        target_character = await player_repository.get_active_character(target_player)
        if not target_character:
            await interaction.followup.send(
                f"{member.mention} needs to create a character first. "
                f"Tell them to use `/character create` and `/character use`.",
                ephemeral=True,
            )
            return

        # Check if target player is already in a game session
        target_session = await player_repository.get_game_session(target_player)
        if target_session:
            if target_session.id == inviter_session.id:
                await interaction.followup.send(
                    f"{member.mention} is already in this game session.", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"{member.mention} is already in another game session. "
                    f"They need to leave it first with `/game leave`.",
                    ephemeral=True,
                )
            return

        # Check session capacity (respect max_players limit)
        current_players = await game_session_repository.players(inviter_session)
        if len(current_players) >= inviter_session.max_players:
            await interaction.followup.send(
                f"The game session is full (max {inviter_session.max_players} players). "
                f"Current players: {len(current_players)}/{inviter_session.max_players}",
                ephemeral=True,
            )
            return

        # Add player to session
        await game_session_repository.add_player(target_player, inviter_session)
        await game_session_repository.add_character(target_character, inviter_session)

        # Apply catch-up restoration when player joins
        character_repository = CharacterRepository(self.postgres_manager)
        target_character = await character_repository.catch_up_restoration_on_session_start(
            target_character
        )

        # Get the game channel
        channel = await find_channel(self.bot, inviter_session.name)
        if not channel:
            self.logger.warning(f"Channel not found for game session: {inviter_session.name}")
            await interaction.followup.send(
                "Game session channel not found. Please contact an administrator.",
                ephemeral=True,
            )
            return

        # Add player to session role
        await self._add_player_to_session_role(member, inviter_session)

        # Get character class for introduction
        character_class = await character_repository.get_character_class(target_character)

        # Introduce the new character to the party
        async with channel.typing():
            await self.message_processor.agent_run(
                game_session=inviter_session,
                channel=channel,
                message=f"Introduce {target_character.name} ({character_class.name}) to the party. Maintain theme and lore of the game session.",
                player=target_player,
                character=target_character,
                characters=await game_session_repository.characters(inviter_session),
            )

        # Notify both players
        await interaction.followup.send(
            f"✅ {member.mention} has been added to the game session!", ephemeral=True
        )

        # Send welcome DM to the added player
        try:
            channel_link = f"https://discord.com/channels/{channel.guild.id}/{channel.id}"
            await send_dm(
                self.bot,
                member,
                f"🎮 **Welcome to the game session!**\n\n"
                f"You've been invited to join **{inviter_session.name}** by {interaction.user.mention}.\n\n"
                f"**Your character:** {target_character.name} ({character_class.name})\n\n"
                f"Join the session here: <#{channel.id}>\n"
                f"Or use this link: {channel_link}\n\n"
                f"See you in the game! 👋",
            )
        except Exception as e:
            self.logger.warning(f"Failed to send DM to {member.display_name}: {e}")

    @game.command(name="remove", description="Remove a player from your game session")
    @app_commands.describe(
        player="User to remove",
    )
    async def remove_player(self, interaction: discord.Interaction, player: discord.Member):
        """Remove a specific player from the current game session. Only the session creator can use this."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        game_session_repository = GameSessionRepository(self.postgres_manager)
        player_repository = PlayerRepository(self.postgres_manager)

        # Check if the command user is in a game session
        remover = await player_repository.get_by_discord_id(interaction.user.id)
        if not remover:
            await interaction.followup.send(
                "You are not registered as a player. Please use `/character create` first.",
                ephemeral=True,
            )
            return

        remover_session = await player_repository.get_game_session(remover)
        if not remover_session:
            await interaction.followup.send(
                "You are not currently in a game session.",
                ephemeral=True,
            )
            return

        # Check if user is the session creator
        if not await self._is_session_creator(remover, remover_session):
            await interaction.followup.send(
                "Only the game session creator can remove players.",
                ephemeral=True,
            )
            return

        # Check if trying to remove themselves
        if player.id == interaction.user.id:
            await interaction.followup.send(
                "You cannot remove yourself. Use `/game leave` to leave the session.",
                ephemeral=True,
            )
            return

        # Skip GM users - they're already in every game session and shouldn't be removed
        if await self._has_gm_role(player):
            await interaction.followup.send(
                f"{player.mention} is a GM and is in all game sessions. Cannot remove GM from sessions.",
                ephemeral=True,
            )
            return

        # Get the target player
        target_player = await player_repository.get_by_discord_id(player.id)
        if not target_player:
            await interaction.followup.send(
                f"{player.mention} is not registered as a player.",
                ephemeral=True,
            )
            return

        # Check if target player is in this session by checking the session's players list
        session_players = await game_session_repository.players(remover_session)
        target_player_in_session = any(p.id == target_player.id for p in session_players)
        if not target_player_in_session:
            await interaction.followup.send(
                f"{player.mention} is not in this game session.",
                ephemeral=True,
            )
            return

        # Get target player's character
        target_character = await player_repository.get_active_character(target_player)
        if target_character:
            # Remove character from session
            await game_session_repository.remove_character(target_character, remover_session)

        # Remove player from session
        await game_session_repository.remove_player(target_player, remover_session)
        self.metrics.record_game_session("player_left")

        # Remove player from session role
        guild = self.bot.guilds[0] if self.bot.guilds else None
        if guild:
            member = guild.get_member(player.id)
            if member:
                await self._remove_player_from_session_role(member, remover_session)

            # Status changes are handled via DMs and ephemeral command responses
            # No need to announce removal via GM to avoid polluting the channel

        # Notify the remover
        await interaction.followup.send(
            f"✅ {player.mention} has been removed from the game session.",
            ephemeral=True,
        )

        # Send DM to the removed player
        try:
            await send_dm(
                self.bot,
                player,
                f"You have been removed from the game session **{remover_session.name}** by {interaction.user.mention}.",
            )
        except Exception as e:
            self.logger.warning(f"Failed to send DM to {player.display_name}: {e}")

    @game.command(name="leave", description="Leave a game session")
    async def leave(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        game_session_repository = GameSessionRepository(self.postgres_manager)
        player_repository = PlayerRepository(self.postgres_manager)

        player = await player_repository.get_by_discord_id(interaction.user.id)
        character = await player_repository.get_active_character(player)

        player_session = await player_repository.get_game_session(player)
        if not player_session:
            await interaction.followup.send("You are not playing in a game", ephemeral=True)
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
            await interaction.followup.send("You have left the game session", ephemeral=True)

            # Remove player from session role
            await self._remove_player_from_session_role(interaction.user, player_session)

            # Status changes are handled via DMs and ephemeral command responses
            # No need to announce leave via GM to avoid polluting the channel

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

                help_text += f"`/{command.parent.name} {command.name}` - {command.description}\n"

        embed = discord.Embed(
            title="Game command help",
            description=help_text,
            color=discord.Color.red(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @tasks.loop(minutes=1.0)
    async def check_game_sessions(self):
        game_session_repository = GameSessionRepository(self.postgres_manager)
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
                    game_session = await game_session_repository.from_channel(channel)
                    # Reset idle timer on resume - this prevents sessions from being closed due to idle time during bot downtime
                    # Note: Game time continues to advance and will fast-forward on startup
                    last_active = datetime.now(UTC)

                    self.active_game_channels[channel_name] = {
                        "last_active_at": last_active,
                        "game_session": game_session,
                        "history": await self.message_processor.load_history(game_session) if game_session else [],
                    }

                    self.logger.debug(
                        f"Added active game session channel: {channel.name} to active game channels "
                        f"(last active: {last_active})"
                    )

                # Check if the channel is idle
                channel_age = (
                    datetime.now(UTC) - self.active_game_channels[channel_name]["last_active_at"]
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

            # Role-session synchronization and validation
            # Validate all sessions have roles and sync players
            for session in db_sessions:
                try:
                    # Check if role exists for session
                    role = await self._get_session_role(session)
                    if not role:
                        # Session exists but role missing - create it and sync players
                        self.logger.warning(
                            f"Session {session.id} ({session.name}) has no matching role - creating role"
                        )
                        try:
                            role = await self._create_session_role(session)
                            # Sync all players to the new role
                            session_players = await game_session_repository.players(session)
                            guild = self.bot.guilds[0] if self.bot.guilds else None
                            if guild:
                                for player in session_players:
                                    member = guild.get_member(player.discord_id)
                                    if member:
                                        await self._add_player_to_session_role(member, session)
                        except Exception as e:
                            self.logger.error(
                                f"Failed to create missing role for session {session.id}: {e}",
                                exc_info=True
                            )
                    else:
                        # Role exists - validate player-role sync
                        await self._validate_session_role_sync(session)
                except Exception as e:
                    self.logger.error(
                        f"Error during role-session sync for session {session.id}: {e}",
                        exc_info=True
                    )

            # Clean up orphaned roles (roles that don't have a matching session)
            guild = self.bot.guilds[0] if self.bot.guilds else None
            if guild:
                db_session_names = {session.name for session in db_sessions}
                for role in guild.roles:
                    # Check if role name matches a session name pattern
                    # Only check roles that could be session roles (lowercase with hyphens)
                    if role.name and "-" in role.name and role.name.islower():
                        # Check if this role corresponds to a session
                        if role.name not in db_session_names:
                            # Orphaned role - check if it's a session role by checking if bot created it
                            # For now, we'll be conservative and only delete if we're certain
                            # In practice, session roles should always have a matching session
                            # But we'll log it for manual review rather than auto-deleting
                            self.logger.debug(
                                f"Found potential orphaned role '{role.name}' - no matching session found"
                            )

            # Remove channels from active game
            self.logger.debug(
                f"Checked {len(self.game_session_category.text_channels)} game session channels for idle sessions"
            )

    @check_game_sessions.before_loop
    async def before_check_game_sessions(self):
        await self.bot.wait_until_ready()
        self.logger.info("Started checking game sessions for idle channels")

    @tasks.loop(seconds=1.0)
    async def restore_character_resources(self):
        """
        Background task that runs every second to restore character resources
        for characters in active game sessions.
        """
        if not self.game_session_category:
            return

        game_session_repository = GameSessionRepository(self.postgres_manager)
        character_repository = CharacterRepository(self.postgres_manager)

        try:
            # Iterate through all active game sessions
            for channel_name, channel_data in self.active_game_channels.items():
                game_session = channel_data.get("game_session")
                if not game_session:
                    continue

                # Get all characters in this game session
                characters_data = await game_session_repository.characters(game_session)
                for character, character_class in characters_data:
                    if not character.last_resource_update:
                        # Initialize if missing
                        character.last_resource_update = datetime.now(UTC)
                        await character_repository.update(character)
                        continue

                    # Check if character is already at full resources
                    is_at_full_resources = (
                        character.current_health >= character.max_health
                        and character.current_stamina >= character.max_stamina
                        and character.current_tech_power >= character.max_tech_power
                        and character.current_armor >= character.max_armor
                    )

                    # If at full resources, skip restoration calculation entirely
                    # (restoration can only increase resources, so if already at max, nothing will change)
                    if is_at_full_resources:
                        # Skip update - character is already at full resources
                        continue

                    # Calculate actual elapsed time since last update
                    # IMPORTANT: We use the actual elapsed time, not an assumed 1.0 second interval
                    # This ensures accurate restoration even with timing variance in task execution
                    now = datetime.now(UTC)
                    elapsed_seconds = (now - character.last_resource_update).total_seconds()

                    # Process if at least 0.9 seconds have elapsed (accounts for timing variance)
                    # This threshold prevents processing too frequently, but we always use actual elapsed time
                    if elapsed_seconds >= 0.9:
                        # Store original resource values to check if anything changed
                        original_health = character.current_health
                        original_stamina = character.current_stamina
                        original_tech_power = character.current_tech_power
                        original_armor = character.current_armor

                        # Apply restoration using actual elapsed time (not assumed 1.0 second)
                        # This accounts for timing variance: if 1.05 seconds passed, restore for 1.05 seconds
                        restore_resources(character, elapsed_seconds)

                        # Check if any resources were actually restored (use small tolerance for floating point)
                        tolerance = 0.01
                        resources_changed = (
                            abs(character.current_health - original_health) > tolerance
                            or abs(character.current_stamina - original_stamina) > tolerance
                            or abs(character.current_tech_power - original_tech_power) > tolerance
                            or abs(character.current_armor - original_armor) > tolerance
                        )

                        # Only update database if resources actually changed
                        if resources_changed:
                            # Update last_resource_update timestamp to the current time
                            # Using actual elapsed time for restoration ensures accuracy even with timing variance
                            # The timestamp tracks when we last processed, not when we "should have" processed
                            character.last_resource_update = now
                            await character_repository.update(character)
                        # If nothing changed, skip database write to avoid unnecessary updates
                        # Note: We don't update last_resource_update if nothing changed to prevent
                        # timestamp drift when character is at full resources

        except Exception as e:
            self.logger.error(f"Error in restore_character_resources: {e}", exc_info=True)

    @restore_character_resources.before_loop
    async def before_restore_character_resources(self):
        await self.bot.wait_until_ready()
        self.logger.info("Started character resource restoration task")

    async def create_game_session(
        self,
        member: discord.Member,
        open_to_all: bool = False,
        users: list[discord.User] | None = None,
    ) -> GameSession:
        self.logger.info(
            f"create_game_session called for {member.display_name} with "
            f"users={users}, users_len={len(users) if users else 0}, open_to_all={open_to_all}"
        )
        # Create game session entry in PostgreSQL and associate with player
        player_repository = PlayerRepository(self.postgres_manager)
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
            return None

        if not player_character:
            await send_dm(
                self.bot,
                member,
                "You have no active character. Select one with `/character use`",
            )
            await move_member_to_voice_channel(self.bot, member)
            return None

        if len(self.active_game_channels) >= self.bot.game_settings.max_game_sessions:
            await send_dm(
                self.bot,
                member,
                "All game sessions are currently in use. Please try again later.",
            )
            await move_member_to_voice_channel(self.bot, member)
            return None

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

            return None

        # CRITICAL: Check all invited users for existing sessions BEFORE creating the new session
        # This prevents race conditions where a user could create their own session while being added to another
        game_session_repository = GameSessionRepository(self.postgres_manager)
        if users:
            guild = member.guild
            users_already_in_session = []
            for user in users:
                # Skip GM users - they're already in every game session
                member_user = guild.get_member(user.id)
                if member_user and await self._has_gm_role(member_user):
                    continue
                
                # Get or create the player
                target_player = await player_repository.get_by_discord_id(user.id)
                if target_player:
                    target_session = await player_repository.get_game_session(target_player)
                    if target_session:
                        users_already_in_session.append((user, target_session))
            
            if users_already_in_session:
                # Build error message listing all users already in sessions
                error_parts = []
                for user, session in users_already_in_session:
                    error_parts.append(f"{user.mention} is already in session '{session.name}'")
                
                await send_dm(
                    self.bot,
                    member,
                    f"Cannot create game session. The following users are already in a game session:\n" + "\n".join(error_parts) + "\n\nPlease ask them to leave their current session first, or create the session without them.",
                )
                await move_member_to_voice_channel(self.bot, member)
                return None

        # Generate a new channel name, check DB for duplicates and generate a new name if needed

        self.logger.debug("Generating new game session name")
        channel_name = NameGenerator.generate_cyberpunk_channel_name()

        counter = 1
        while await game_session_repository.get_by_field("name", channel_name):
            self.logger.debug(
                f"Duplicate game session name found, generating new name ({counter}/3)"
            )
            channel_name = NameGenerator.generate_cyberpunk_channel_name()

            counter += 1

            if counter > 3:
                self.logger.warning("Failed to generate unique game session name after 3 attempts")
                await send_dm(
                    self.bot,
                    member,
                    "Failed to generate game session after 3 attempts. Please try again later.",
                )
                await self._move_member_from_join_channel(member)
                return None

        game_session = GameSession(
            name=channel_name,
            channel_id=None,
            is_open=open_to_all,
            created_at=datetime.now(UTC),
            last_active_at=datetime.now(UTC),
        )

        await game_session_repository.upsert(game_session)
        await game_session_repository.add_player(player, game_session)
        await game_session_repository.add_character(player_character, game_session)

        # CRITICAL: Add invited users to the session IMMEDIATELY after creating it
        # This prevents race conditions where a user could create their own session
        # while being added to this one. We do this before Discord channel setup
        # to ensure database state is consistent.
        character_repository = CharacterRepository(self.postgres_manager)
        self.logger.info(
            f"Early user addition: users={users}, users_len={len(users) if users else 0}, "
            f"users_ids={[u.id for u in users] if users else []}"
        )
        if users:
            guild = member.guild
            failed_players = []  # Track players who fail citizen role check
            for user in users:
                # Skip GM users - they're already in every game session
                member_user = guild.get_member(user.id)
                if member_user and await self._has_gm_role(member_user):
                    continue
                
                # Check if user has citizen role - required to join sessions
                if member_user and not await self._has_player_role(member_user):
                    failed_players.append((user, member_user))
                    self.logger.warning(
                        f"User {member_user.display_name} (ID: {member_user.id}) does not have citizen role - cannot add to session"
                    )
                    continue
                
                # Get or create the player
                target_player = await player_repository.get_by_discord_id(user.id)
                if not target_player:
                    target_player = Player.from_member(member_user) if member_user else None
                    if target_player:
                        target_player = await player_repository.upsert(target_player)
                
                if target_player:
                    # Double-check they're not in another session (safety check)
                    target_session = await player_repository.get_game_session(target_player)
                    if not target_session:
                        # Get their active character first - need it to add to session
                        target_character = await player_repository.get_active_character(target_player)
                        if target_character:
                            # Add to session immediately (both player and character)
                            await game_session_repository.add_player(target_player, game_session)
                            await game_session_repository.add_character(target_character, game_session)
                            # Apply catch-up restoration
                            await character_repository.catch_up_restoration_on_session_start(
                                target_character
                            )
                        # If no character, we'll skip them here and _add_users_to_session_at_start will handle the error
            
            # Send warnings for players who failed citizen role check
            if failed_players:
                config = self._get_config()
                rules_channel_name = config.game_rules_channel_name
                rules_channel_mention = f"#{rules_channel_name}" if rules_channel_name else "the rules channel"
                
                # Build warning message for creator
                failed_mentions = [m.mention for _, m in failed_players]
                warning_message = (
                    f"⚠️ **Some players could not be added to the session:**\n\n"
                    f"The following players do not have the **citizen** role and cannot join game sessions:\n"
                    f"{', '.join(failed_mentions)}\n\n"
                    f"**To fix this:**\n"
                    f"1. Ask them to accept the server rules in {rules_channel_mention}\n"
                    f"2. Once they have the citizen role, you can add them to the session using `/game add`\n\n"
                    f"Players need the citizen role to participate in game sessions for security and rule compliance."
                )
                try:
                    await send_dm(self.bot, member, warning_message)
                except Exception as e:
                    self.logger.warning(f"Failed to send citizen role warning to session creator: {e}")
                
                # Send warnings to failed players
                for user, member_user in failed_players:
                    player_warning = (
                        f"⚠️ **Cannot Join Game Session**\n\n"
                        f"You were invited to join a game session, but you don't have the **citizen** role.\n\n"
                        f"**To get the citizen role:**\n"
                        f"1. Go to {rules_channel_mention}\n"
                        f"2. Accept the server rules by reacting to the required messages\n"
                        f"3. Once you have the citizen role, ask the session creator to invite you again using `/game add`\n\n"
                        f"The citizen role is required to participate in game sessions for security and rule compliance."
                    )
                    try:
                        await send_dm(self.bot, member_user, player_warning)
                    except Exception as e:
                        self.logger.warning(f"Failed to send citizen role warning to {member_user.display_name}: {e}")

        # Track metrics
        self.metrics.record_game_session("created")
        self.metrics.set_active_game_sessions(len(self.active_game_channels) + 1)

        # Apply catch-up restoration when player creates/joins session
        player_character = await character_repository.catch_up_restoration_on_session_start(
            player_character
        )

        # CRITICAL: Create session role FIRST (before channel creation) - enforces 1:1 relationship
        try:
            session_role = await self._create_session_role(game_session)
            # Role is automatically added to guild.roles cache when created
            # No need to refresh - the role object returned is the one we'll use
        except Exception as e:
            self.logger.error(
                f"Failed to create role for session {game_session.id}: {e}",
                exc_info=True
            )
            await send_dm(
                self.bot,
                member,
                "Failed to create game session role. Please contact an administrator.",
            )
            await self._move_member_from_join_channel(member)
            # Clean up the session from database
            await game_session_repository.delete(game_session.id)
            return None

        display_channel_name = channel_name
        if not open_to_all:
            display_channel_name = f"🔒-{channel_name}"

        channel = await create_text_channel(
            self.bot, display_channel_name, self.game_session_category
        )

        game_session.channel_id = channel.id
        await game_session_repository.upsert(game_session)

        # Set channel permissions for session role
        session_role_overwrite = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_messages=True,
            read_message_history=True,
            add_reactions=True,
            use_application_commands=True,
            create_instant_invite=False,
        )
        await channel.set_permissions(session_role, overwrite=session_role_overwrite)

        config = self._get_config()
        player_role_name = config.role_management_player_role_name
        player_role = await self.bot.get_role(player_role_name)
        if player_role:
            # Set player role to deny access by default
            # Session role permissions will override this for players in the session
            player_overwrite = discord.PermissionOverwrite(
                view_channel=False,
                create_instant_invite=False,
                send_messages=False,
                read_messages=True,
                read_message_history=True,
                add_reactions=False,
                use_application_commands=False,
            )
            await channel.set_permissions(player_role, overwrite=player_overwrite)
        else:
            self.logger.warning(f"Player role '{player_role_name}' not found")

        moderator_role_name = config.role_management_moderator_role_name
        moderator_role = await self.bot.get_role(moderator_role_name)
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
            self.logger.warning(f"Moderator role '{moderator_role_name}' not found")

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

        # Add session creator to session role
        await self._add_player_to_session_role(member, game_session)

        # Get starting location name for welcome message
        starting_location_name = "The Undergrid"
        if player_character.current_location:
            try:
                from ds_common.repository.location_node import LocationNodeRepository

                node_repository = LocationNodeRepository(self.postgres_manager)
                location_node = await node_repository.get_by_id(player_character.current_location)
                if location_node:
                    starting_location_name = location_node.location_name
            except Exception:
                pass  # Use default if lookup fails

        # Build welcome message with invited players
        welcome_mentions = [member.mention]
        if users:
            guild = self.bot.guilds[0] if self.bot.guilds else None
            if guild:
                for user in users:
                    member_user = guild.get_member(user.id)
                    if member_user and not await self._has_gm_role(member_user):
                        welcome_mentions.append(member_user.mention)
        
        # Use correct grammar based on number of players
        if len(welcome_mentions) == 1:
            welcome_text = f"Welcome to your new game session {welcome_mentions[0]}!\n"
            welcome_text += f"You find yourself in **{starting_location_name}**, deep in the Undergrid beneath Neotopia.\n"
        else:
            welcome_text = f"Welcome to your new game session {', '.join(welcome_mentions)}!\n"
            welcome_text += f"You find yourselves in **{starting_location_name}**, deep in the Undergrid beneath Neotopia.\n"
        
        welcome_text += "Please review the game rules and setup in the #rules channel.\n"
        welcome_text += "Remember that you can use `/game help` for help with game commands.\n"
        welcome_text += f"To help ensure the best experience for all players, sessions that have been idle for {self.bot.game_settings.max_game_session_idle_duration} minutes will be automatically deleted."
        
        await channel.send(welcome_text, delete_after=60.0)

        # Send DM to session creator with channel link
        try:
            character_class = await character_repository.get_character_class(player_character)
            channel_link = f"https://discord.com/channels/{channel.guild.id}/{channel.id}"
            await send_dm(
                self.bot,
                member,
                f"🎮 **Game session started!**\n\n"
                f"Your game session **{game_session.name}** has been created.\n\n"
                f"**Your character:** {player_character.name} ({character_class.name})\n\n"
                f"Join the session here: <#{channel.id}>\n"
                f"Or use this link: {channel_link}\n\n"
                f"See you in the game! 👋",
            )
        except Exception as e:
            self.logger.warning(f"Failed to send DM to session creator {member.display_name}: {e}")

        channel.slowmode_delay = self.bot.game_settings.game_channel_slowmode_delay
        self.logger.debug(
            f"Set slowmode delay to {self.bot.game_settings.game_channel_slowmode_delay} seconds"
        )
        await move_member_to_voice_channel(self.bot, member)

        # Add invited users to the session
        self.logger.info(
            f"About to add invited users to session '{game_session.name}'. "
            f"users parameter: {users}, type: {type(users)}, length: {len(users) if users else 0}"
        )
        if users:
            self.logger.info(
                f"Calling _add_users_to_session_at_start with {len(users)} user(s): "
                f"{[u.display_name if hasattr(u, 'display_name') else str(u) for u in users]}"
            )
            await self._add_users_to_session_at_start(
                users, member, game_session, channel, player_repository, game_session_repository
            )
        else:
            self.logger.warning(
                f"No users provided to add to session '{game_session.name}' - users parameter is {users}"
            )

        self.active_game_channels[game_session.name] = {
            "last_active_at": datetime.now(UTC),
            "game_session": game_session,
            "history": [],
        }
        await game_session_repository.update_last_active_at(channel)

        return game_session

    async def end_game_session(self, session: GameSession):
        """
        End the game session the player is playing in
        """
        # Condense session to episode in background
        try:
            from openai import AsyncOpenAI

            # Only condense if embedding service is available
            config = self._get_config()
            embedding_base_url = config.ai_embedding_base_url
            embedding_api_key = config.ai_embedding_api_key

            if embedding_base_url or embedding_api_key:
                from ds_common.memory.memory_processor import MemoryProcessor

                # Build client kwargs - always include api_key (required by client library)
                # Use dummy key for local services that don't require authentication
                client_kwargs = {
                    "api_key": embedding_api_key
                    if embedding_api_key
                    else "sk-ollama-local-dummy-key-not-used"
                }
                if embedding_base_url:
                    client_kwargs["base_url"] = embedding_base_url

                openai_client = AsyncOpenAI(**client_kwargs)
                # Get model and dimensions from config
                embedding_model = config.ai_embedding_model
                embedding_dimensions = config.ai_embedding_dimensions

                # Try to get Redis client for memory embeddings (database 1)
                redis_client = self._create_redis_client(config.redis_db_memory)

                memory_processor = MemoryProcessor(
                    self.postgres_manager,
                    openai_client,
                    redis_client=redis_client,
                    embedding_model=embedding_model,
                    embedding_dimensions=embedding_dimensions,
                )

                # Run in background task
                async def condense_episode():
                    try:
                        episode_id = await memory_processor.condense_session_to_episode(session.id)
                        self.logger.info(f"Condensed session {session.id} to episode {episode_id}")
                    except Exception as e:
                        self.logger.error(f"Failed to condense session to episode: {e}")

                # Schedule background task
                self.bot.loop.create_task(condense_episode())
        except Exception as e:
            self.logger.warning(f"Failed to schedule episode condensation: {e}")
        game_session_repository = GameSessionRepository(self.postgres_manager)
        players_list = await game_session_repository.players(session)

        # Send ending notification to all players
        for player in players_list:
            member = self.bot.guilds[0].get_member(player.discord_id)
            if member:
                try:
                    await send_dm(self.bot, member, "Game session ending...")
                except Exception as e:
                    self.logger.warning(f"Failed to send ending DM to {member.display_name}: {e}")
                await move_member_to_voice_channel(self.bot, member)

        # Delete game session and all related data
        await self._delete_game_session(session)

        channel = await find_channel(self.bot, session.name)
        if channel:
            if channel.id in self.active_game_channels:
                del self.active_game_channels[session.name]
            await channel.delete()

        # Track metrics
        self.metrics.record_game_session("ended")
        self.metrics.set_active_game_sessions(len(self.active_game_channels))

        # Send completion notification to all players
        for player in players_list:
            member = self.bot.guilds[0].get_member(player.discord_id)
            if member:
                try:
                    await send_dm(self.bot, member, "Game session ended!")
                except Exception as e:
                    self.logger.warning(
                        f"Failed to send completion DM to {member.display_name}: {e}"
                    )

    async def _delete_game_session(self, game_session: GameSession) -> None:
        """Delegate to SessionManager."""
        await self.session_manager.delete_game_session(game_session)
        """
        Safely delete a game session and all related data.

        Deletes in the correct order to avoid foreign key constraint violations:
        1. Session memory records
        2. GM history records
        3. Junction table entries (players, characters)
        4. Game session itself

        Args:
            game_session: GameSession instance to delete
        """
        from sqlmodel import select

        from ds_common.models.game_master import GMHistory
        from ds_common.models.junction_tables import (
            GameSessionCharacter,
            GameSessionPlayer,
        )
        from ds_common.models.session_memory import SessionMemory
        from ds_common.repository.character import CharacterRepository

        async with self.postgres_manager.get_session() as sess:
            # 0. Clean up quest items from characters before deleting quest relationships
            from ds_common.repository.quest import QuestRepository

            quest_repo = QuestRepository(self.postgres_manager)
            character_quests = await quest_repo.get_quests_by_session(game_session.id)

            character_repo = CharacterRepository(self.postgres_manager)
            for char_quest in character_quests:
                if char_quest.items_given:
                    # Get character and remove quest items
                    character = await character_repo.get_by_id(char_quest.character_id)
                    if character and character.inventory:
                        inventory = character.inventory
                        updated_inventory = []
                        items_removed = []

                        for inv_item in inventory:
                            item_removed = False
                            for quest_item in char_quest.items_given:
                                # Match by instance_id (preferred) or name
                                if inv_item.get("instance_id") == quest_item.get("instance_id"):
                                    items_removed.append(
                                        {
                                            "name": inv_item.get("name"),
                                            "quantity": inv_item.get("quantity", 0),
                                        }
                                    )
                                    item_removed = True
                                    break
                                if inv_item.get("name") == quest_item.get("name"):
                                    # Reduce quantity
                                    current_qty = inv_item.get("quantity", 0)
                                    remove_qty = quest_item.get("quantity", 0)
                                    new_qty = current_qty - remove_qty

                                    if new_qty > 0:
                                        inv_item["quantity"] = new_qty
                                        updated_inventory.append(inv_item)
                                    items_removed.append(
                                        {
                                            "name": inv_item.get("name"),
                                            "quantity": min(current_qty, remove_qty),
                                        }
                                    )
                                    item_removed = True
                                    break

                            if not item_removed:
                                updated_inventory.append(inv_item)

                        character.inventory = updated_inventory
                        await character_repo.update(character)
                        self.logger.info(
                            f"Cleaned up {len(items_removed)} quest items from character {character.id} "
                            f"when session {game_session.id} ended: {[item['name'] for item in items_removed]}"
                        )

            # 1. Delete session memory records
            stmt = select(SessionMemory).where(SessionMemory.session_id == game_session.id)
            result = await sess.execute(stmt)
            for memory in result.scalars().all():
                await sess.delete(memory)

            # 2. Delete GM history records
            stmt = select(GMHistory).where(GMHistory.game_session_id == game_session.id)
            result = await sess.execute(stmt)
            for history in result.scalars().all():
                await sess.delete(history)

            # 3. Delete junction table entries
            # Delete CharacterQuest entries (quest items already cleaned up above)
            for char_quest in character_quests:
                await sess.delete(char_quest)

            # Delete GameSessionCharacter entries
            stmt = select(GameSessionCharacter).where(
                GameSessionCharacter.game_session_id == game_session.id
            )
            result = await sess.execute(stmt)
            for junction in result.scalars().all():
                await sess.delete(junction)

            # Delete GameSessionPlayer entries
            stmt = select(GameSessionPlayer).where(
                GameSessionPlayer.game_session_id == game_session.id
            )
            result = await sess.execute(stmt)
            for junction in result.scalars().all():
                await sess.delete(junction)

            await sess.commit()

        # 4. Now delete the game session itself
        game_session_repository = GameSessionRepository(self.postgres_manager)
        await game_session_repository.delete(game_session.id)

        # 5. Delete the session role (strict 1:1 relationship)
        await self._delete_session_role(game_session)

    async def _init_game_session_join_channel(self) -> discord.VoiceChannel | None:
        """
        Initialize the game session join channel
        """
        if self.game_session_join_channel:
            return self.game_session_join_channel

        game_session_join_channel = await self._find_channel("Join to Play")

        if not game_session_join_channel:
            game_session_join_channel = await self._create_voice_channel("Join to Play")

            self.logger.debug(f"Created game session join channel: {game_session_join_channel}")

            # Ensure player role can join the channel
            config = self._get_config()
            player_role_name = config.role_management_player_role_name
            player_role = self.bot.guilds[0].get_role(player_role_name)
            if player_role:
                await self.game_session_join_channel.set_permissions(player_role, connect=True)

            else:
                self.logger.warning(f"Player role '{player_role_name}' not found")

            # Ensure GM role can join/monitor the channel
            gm_role_name = config.role_management_gm_role_name
            GM_role = self.bot.guilds[0].get_role(gm_role_name)
            if GM_role:
                await self.game_session_join_channel.set_permissions(
                    GM_role, move_members=True, view_channel=True
                )

            else:
                self.logger.warning(f"GM role '{gm_role_name}' not found")

        return game_session_join_channel

    async def _init_game_sessions(self):
        self.logger.debug("Initializing game sessions")
        game_session_repository = GameSessionRepository(self.postgres_manager)

        for game_session in await game_session_repository.get_all():
            channel = await find_channel(self.bot, game_session.name, self.game_session_category)
            if not channel:
                # Channel doesn't exist, clean up orphaned game session
                await self._delete_game_session(game_session)
                continue

            history = await self.message_processor.load_history(game_session)
            # Reset idle timer on resume - this prevents sessions from being closed due to idle time during bot downtime
            # Note: Game time continues to advance and will fast-forward on startup
            self.active_game_channels[game_session.name] = {
                "last_active_at": datetime.now(UTC),
                "game_session": game_session,
                "history": history,
            }

        self.logger.debug(
            f"Loaded {len(self.active_game_channels)} active game sessions from database"
        )

    async def _notify_active_sessions_shutdown(self) -> None:
        """Send shutdown notification to service announcements channel if configured."""
        # Build shutdown message
        shutdown_message = "**🔴 System Maintenance**\n\n*The system is going down for maintenance. Game time will continue to advance and catch up when we return. We'll be back soon.*"

        # Post to service announcements channel if configured
        if self.bot.channel_service_announcements:
            try:
                await self.bot.channel_service_announcements.send(shutdown_message)
                self.logger.info("Posted shutdown notification to service announcements channel")
            except Exception as e:
                self.logger.warning(f"Failed to post to service announcements channel: {e}")

    async def _notify_active_sessions_startup(self) -> None:
        """Send startup notification to service announcements channel if configured."""
        # Build detailed startup message with calendar information
        startup_message = await self._build_startup_message()

        # Post detailed message to service announcements channel if configured
        if self.bot.channel_service_announcements:
            try:
                await self.bot.channel_service_announcements.send(startup_message)
                self.logger.info("Posted startup notification to service announcements channel")
            except Exception as e:
                self.logger.warning(f"Failed to post to service announcements channel: {e}")

    async def _build_startup_message(self) -> str:
        """
        Build a detailed startup message with calendar information and other relevant details.

        Returns:
            Formatted startup message string
        """
        try:
            from ds_common.memory.calendar_service import CalendarService
            from ds_common.memory.game_time_service import GameTimeService

            game_time_service = GameTimeService(self.postgres_manager)
            calendar_service = CalendarService(self.postgres_manager, game_time_service)

            # Get current game date
            current_date = await calendar_service.get_current_game_date()
            game_time = await game_time_service.get_current_game_time()

            # Get additional calendar info
            month_name = await game_time_service.get_current_month_name()
            cycle_animal = await game_time_service.get_current_cycle_animal()
            time_of_day = await game_time_service.get_time_of_day()
            active_events = await calendar_service.get_active_events()

            # Build message
            message_parts = [
                "**🟢 System Online**",
                "",
                "*The system is back online. Game sessions have resumed.*",
                "",
                "**📅 Current Game Date:**",
            ]

            # Date information
            date_info = f"Year {current_date['year']}, Day {current_date['day']}"
            if month_name:
                date_info += f" ({month_name})"
            date_info += f", Hour {current_date['hour']:02d}"
            if game_time.game_minute is not None:
                date_info += f":{game_time.game_minute:02d}"
            message_parts.append(date_info)

            # Season and day of week
            info_line = f"**{current_date['season']}** • {current_date['day_of_week']}"
            if cycle_animal:
                info_line += f" • Year of the {cycle_animal}"
            info_line += f" • {time_of_day}"
            message_parts.append(info_line)

            # Active calendar events
            if active_events:
                message_parts.append("")
                message_parts.append("**📆 Active Events:**")
                for event in active_events[:5]:  # Limit to 5 events
                    message_parts.append(f"• {event.name}")
                if len(active_events) > 5:
                    message_parts.append(f"*...and {len(active_events) - 5} more*")

            # Active game sessions count
            if self.active_game_channels:
                session_count = len(self.active_game_channels)
                message_parts.append("")
                message_parts.append(f"**🎮 Active Game Sessions:** {session_count}")

            return "\n".join(message_parts)

        except Exception as e:
            self.logger.warning(f"Failed to build detailed startup message: {e}")
            # Fallback to simple message
            return "*The system is back online. Game sessions have resumed.*"

