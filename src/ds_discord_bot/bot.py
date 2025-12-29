import asyncio
import logging
import time
import traceback
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, override

import discord
from discord import Activity, ActivityType, Role, TextChannel
from discord.ext import commands

from ds_common.metrics.service import get_metrics_service
from ds_common.repository.game_settings import GameSettingsRepository

if TYPE_CHECKING:
    from ds_common.models.game_settings import GameSettings

from .extensions import Extension
from .postgres_manager import PostgresManager


class RefreshableGameSettings:
    """
    Wrapper for GameSettings that automatically refreshes from the database
    when attributes are accessed, but at most once per minute.

    This allows game settings to be updated in the database without requiring
    a bot restart, while limiting database queries to prevent excessive load.
    """

    def __init__(
        self,
        initial_settings: "GameSettings",
        postgres_manager: PostgresManager,
        refresh_interval: timedelta = timedelta(minutes=1),
    ):
        self._settings: GameSettings = initial_settings
        self._postgres_manager: PostgresManager = postgres_manager
        self._refresh_interval: timedelta = refresh_interval
        self._last_refresh: datetime = datetime.now(UTC)
        self._logger: logging.Logger = logging.getLogger(__name__)
        self._default_id = initial_settings.id
        self._refresh_lock: asyncio.Lock | None = None
        self._pending_refresh: bool = False

    def _ensure_lock(self) -> asyncio.Lock:
        """Ensure the refresh lock exists (lazy initialization)."""
        if self._refresh_lock is None:
            try:
                loop = asyncio.get_running_loop()
                self._refresh_lock = asyncio.Lock()
            except RuntimeError:
                # No event loop, create a new one (shouldn't happen in practice)
                self._refresh_lock = asyncio.Lock()
        return self._refresh_lock

    async def _refresh_if_needed(self) -> None:
        """Refresh settings from database if the refresh interval has passed."""
        lock = self._ensure_lock()

        # Quick check before acquiring lock (optimization)
        now = datetime.now(UTC)
        if now - self._last_refresh < self._refresh_interval:
            return  # Too soon to refresh

        async with lock:
            # Double-check after acquiring lock (prevents race conditions)
            now = datetime.now(UTC)
            if now - self._last_refresh < self._refresh_interval:
                return  # Another task already refreshed

            if self._pending_refresh:
                return  # Refresh already in progress

            self._pending_refresh = True
            try:
                game_settings_repo = GameSettingsRepository(self._postgres_manager)
                refreshed = await game_settings_repo.get_by_id(self._default_id)
                if refreshed:
                    self._settings = refreshed
                    self._last_refresh = now
                    self._logger.debug("Refreshed game settings from database")
            except Exception as e:
                self._logger.warning(f"Failed to refresh game settings: {e}")
            finally:
                self._pending_refresh = False

    def _schedule_refresh(self) -> None:
        """Schedule a background refresh if needed (non-blocking)."""
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running() and not self._pending_refresh:
                # Schedule refresh in background (fire and forget)
                loop.create_task(self._refresh_if_needed())
        except RuntimeError:
            # No event loop running, skip refresh
            pass

    def __getattribute__(self, name: str) -> Any:
        """Intercept all attribute access to schedule refresh if needed."""
        # Avoid infinite recursion by checking for our own attributes first
        if name.startswith("_") or name in (
            "_settings",
            "_postgres_manager",
            "_refresh_interval",
            "_last_refresh",
            "_logger",
            "_default_id",
            "_refresh_lock",
            "_pending_refresh",
            "_ensure_lock",
            "_refresh_if_needed",
            "_schedule_refresh",
        ):
            return super().__getattribute__(name)

        # Schedule refresh in background (non-blocking)
        try:
            obj = super().__getattribute__("_schedule_refresh")
            obj()
        except Exception:
            # If scheduling fails, continue anyway
            pass

        # Return attribute from wrapped settings
        settings = super().__getattribute__("_settings")
        return getattr(settings, name)

    def __repr__(self) -> str:
        return repr(self._settings)

    def __str__(self) -> str:
        return str(self._settings)


class DSBot(commands.AutoShardedBot):
    def __init__(
        self,
        *args,
        enabled_extensions: list[Extension],
        postgres_manager: PostgresManager,
        **kwargs,
    ):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.enabled_extensions: list[Extension] = enabled_extensions
        self.postgres_manager: PostgresManager = postgres_manager
        self.game_settings: RefreshableGameSettings | None = None
        self.channel_welcome: TextChannel | None = None
        self.channel_bot_commands: TextChannel | None = None
        self.channel_bot_logs: TextChannel | None = None
        self.channel_moderation_logs: TextChannel | None = None
        self.channel_service_announcements: TextChannel | None = None
        self.channel_rules: TextChannel | None = None
        self.metrics = get_metrics_service()
        self._uptime_task: asyncio.Task[Any] | None = None

        super().__init__(
            *args,
            activity=Activity(type=ActivityType.playing, name="in the shadows"),
            **kwargs,
        )

    @override
    async def setup_hook(self) -> None:
        await self.load_game_settings()
        await self.load_extensions()
        # Setup command handlers for metrics
        self.add_listener(self._on_command, name="on_command")
        self.add_listener(self._on_app_command, name="on_app_command")
        self.add_listener(self._on_command_error, name="on_command_error")
        self.add_listener(self._on_app_command_error, name="on_app_command_error")
        self.add_listener(self._on_command_completion, name="on_command_completion")
        self.add_listener(self._on_app_command_completion, name="on_app_command_completion")
        # Setup Discord event handlers for metrics
        self.add_listener(self._on_message, name="on_message")
        self.add_listener(self._on_reaction_add, name="on_reaction_add")
        self.add_listener(self._on_member_join, name="on_member_join")
        self.add_listener(self._on_member_remove, name="on_member_remove")

    @override
    async def on_ready(self) -> None:
        from ds_common.config_bot import get_config

        config = get_config()
        self.channel_welcome = await self.get_channel("👋🏾-welcome")
        self.channel_bot_commands = await self.get_channel("bot-commands")
        self.channel_bot_logs = await self.get_channel("bot-log")
        self.channel_moderation_logs = await self.get_channel("moderator-only")
        service_announcements_name = config.game_service_announcements_channel_name
        self.channel_service_announcements = await self.get_channel(service_announcements_name)
        rules_channel_name = config.game_rules_channel_name
        self.channel_rules = await self.get_channel(rules_channel_name)

        # Update metrics
        self.metrics.set_bot_ready(True)
        self.metrics.set_shard_info(self.shard_id, self.shard_count)
        if self.guilds:
            self.metrics.set_guild_count(len(self.guilds))
        self.metrics.set_user_count(len(self.users))

        # Start uptime update task
        self._uptime_task = asyncio.create_task(self._update_uptime_loop())

        self.logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        self.logger.info(f"Shard ID: {self.shard_id or 'N/A'}")
        self.logger.info(f"Shard Count: {self.shard_count or 'N/A'}")
        self.logger.info(f"Guild: {self.guilds[0].name} (ID: {self.guilds[0].id})")
        self.logger.info(f"User Count: {len(self.users)}")
        self.logger.info(f"Role Count: {len(self.guilds[0].roles)}")
        self.logger.info(f"Game Settings: {self.game_settings}")
        self.logger.info(
            f"Loaded Extensions: {', '.join([extension.name for extension in self.enabled_extensions])}"
        )
        self.logger.info(f"Database: {self.postgres_manager.database_url}")
        self.logger.info(
            f"Bot Commands Channel: {self.channel_bot_commands.name} (ID: {self.channel_bot_commands.id})"
        )
        self.logger.info(
            f"Bot Logs Channel: {self.channel_bot_logs.name} (ID: {self.channel_bot_logs.id})"
        )
        self.logger.info(
            f"Moderation Logs Channel: {self.channel_moderation_logs.name} (ID: {self.channel_moderation_logs.id})"
        )
        self.logger.info("Bot is ready!")

    async def _update_uptime_loop(self) -> None:
        """Periodically update uptime metric."""
        while True:
            try:
                self.metrics.update_uptime()
                await asyncio.sleep(10)  # Update every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error updating uptime metric: {e}")

    async def _on_command(self, ctx: commands.Context) -> None:
        """Track command start time."""
        ctx._command_start_time = time.time()

    async def _on_app_command(
        self,
        interaction: discord.Interaction,
    ) -> None:
        """Track app command start time."""
        interaction._command_start_time = time.time()

    async def _on_command_completion(self, ctx: commands.Context) -> None:
        """Track command completion in metrics."""
        if hasattr(ctx, "_command_start_time"):
            duration = time.time() - ctx._command_start_time
            command_name = ctx.command.name if ctx.command else "unknown"
            self.metrics.record_command(command_name, duration, status="success")

    async def _on_app_command_completion(
        self,
        interaction: discord.Interaction,
        command: discord.app_commands.Command | discord.app_commands.ContextMenu,
    ) -> None:
        """Track app command (slash command) completion in metrics."""
        if hasattr(interaction, "_command_start_time"):
            duration = time.time() - interaction._command_start_time
            command_name = command.name if command else "unknown"
            self.metrics.record_command(command_name, duration, status="success")

    async def _on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        """Track command errors in metrics."""
        duration = 0.0
        if hasattr(ctx, "_command_start_time"):
            duration = time.time() - ctx._command_start_time
        command_name = ctx.command.name if ctx.command else "unknown"
        self.metrics.record_command(command_name, duration, status="error")

    async def _on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError,
    ) -> None:
        """Track app command errors in metrics."""
        duration = 0.0
        if hasattr(interaction, "_command_start_time"):
            duration = time.time() - interaction._command_start_time
        command_name = "unknown"
        if interaction.command:
            command_name = interaction.command.name
        self.metrics.record_command(command_name, duration, status="error")

    async def _on_message(self, message: discord.Message) -> None:
        """Track Discord messages in metrics."""
        if not message.author.bot:
            self.metrics.record_discord_message()

    async def _on_reaction_add(
        self,
        reaction: discord.Reaction,
        user: discord.User | discord.Member,
    ) -> None:
        """Track Discord reactions in metrics."""
        if not user.bot:
            self.metrics.record_discord_reaction()

    async def _on_member_join(self, member: discord.Member) -> None:
        """Track member joins in metrics."""
        self.metrics.record_member_join()

    async def _on_member_remove(self, member: discord.Member) -> None:
        """Track member leaves in metrics."""
        self.metrics.record_member_leave()

    async def load_game_settings(self) -> None:
        """
        Load game settings from database and wrap in RefreshableGameSettings
        for automatic lazy refreshing.
        """
        from uuid import UUID

        self.logger.info("Loading game settings...")
        game_settings_repo = GameSettingsRepository(self.postgres_manager)
        # Try to get default settings (UUID: 00000000-0000-0000-0000-000000000001)
        default_id = UUID("00000000-0000-0000-0000-000000000001")
        settings = await game_settings_repo.get_by_id(default_id)

        if not settings:
            self.logger.info("Game settings not found, creating default...")
            settings = await game_settings_repo.seed_db()
        else:
            self.logger.info("Game settings loaded: %s", settings)

        # Wrap in RefreshableGameSettings for automatic lazy refreshing
        self.game_settings = RefreshableGameSettings(
            initial_settings=settings,
            postgres_manager=self.postgres_manager,
        )

    async def load_extensions(self) -> None:
        """
        Load extensions from enabled_extensions list
        """

        self.logger.info("Loading extensions...")
        for extension in self.enabled_extensions:
            try:
                await self.load_extension(name=extension.value)
            except Exception:
                self.logger.error(
                    f"Failed to load extension {extension.value}: {traceback.format_exc()}"
                )

    async def get_channel(self, channel_name: str) -> TextChannel | None:
        for channel in self.guilds[0].channels:
            if channel.name == channel_name:
                self.logger.debug("Found channel: %s", channel)
                return channel
        return None

    async def get_role(self, role_name: str) -> Role | None:
        for role in self.guilds[0].roles:
            if role.name == role_name:
                self.logger.debug("Found role: %s", role)
                return role
        return None

    async def verify_roles(self) -> None:
        for role in self.guilds[0].roles:
            if role.name == "Player":
                self.logger.debug("Found role: %s", role)

    async def log(self, level: str, message: str) -> None:
        level = level.upper()

        if self.channel_bot_logs:
            await self.channel_bot_logs.send(f"{level}: {message}")

        if level == "WARNING":
            self.logger.warning(message)
        elif level == "ERROR":
            self.logger.error(message)
        elif level == "DEBUG":
            self.logger.debug(message)
        else:
            self.logger.info(message)
