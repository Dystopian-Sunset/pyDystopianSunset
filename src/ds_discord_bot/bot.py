import logging
import traceback
from typing import override

from discord import Activity, ActivityType, Role, TextChannel
from discord.ext import commands

from ds_common.models.game_settings import GameSettings
from ds_common.repository.game_settings import GameSettingsRepository

from .extensions import Extension
from .surreal_manager import SurrealManager


class DSBot(commands.AutoShardedBot):
    def __init__(
        self,
        *args,
        enabled_extensions: list[Extension],
        surreal_manager: SurrealManager,
        **kwargs,
    ):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.enabled_extensions: list[Extension] = enabled_extensions
        self.surreal_manager: SurrealManager = surreal_manager
        self.game_settings: GameSettings | None = None
        self.channel_welcome: TextChannel | None = None
        self.channel_bot_commands: TextChannel | None = None
        self.channel_bot_logs: TextChannel | None = None
        self.channel_moderation_logs: TextChannel | None = None

        super().__init__(
            *args,
            activity=Activity(type=ActivityType.playing, name="in the shadows"),
            **kwargs,
        )

    @override
    async def setup_hook(self) -> None:
        await self.load_game_settings()
        await self.load_extensions()

    @override
    async def on_ready(self) -> None:
        self.channel_welcome = await self.get_channel("👋🏾-welcome")
        self.channel_bot_commands = await self.get_channel("bot-commands")
        self.channel_bot_logs = await self.get_channel("bot-log")
        self.channel_moderation_logs = await self.get_channel("moderator-only")

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
        self.logger.info(f"Database: {self.surreal_manager.url}")
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

    async def load_game_settings(self) -> None:
        """
        Load game settings from database
        """

        self.logger.info("Loading game settings...")
        game_settings_id = GameSettings.create_id("default")
        self.game_settings = await GameSettingsRepository(
            self.surreal_manager
        ).get_by_id(game_settings_id)

        if not self.game_settings:
            self.logger.info("Game settings not found, creating default...")
            self.game_settings = await GameSettingsRepository(
                self.surreal_manager
            ).seed_db()
        else:
            self.logger.info("Game settings loaded: %s", self.game_settings)

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
