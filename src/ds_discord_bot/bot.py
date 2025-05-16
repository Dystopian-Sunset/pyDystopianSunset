import logging
import traceback
from typing import override
from discord.ext import commands
from datetime import datetime, timezone
from surrealdb import AsyncSurreal

from .extensions import Extension
from ds_common.models.discord_user import DiscordUser

class DSBot(commands.AutoShardedBot):
    def __init__(
        self,
        *args,
        enabled_extensions: list[Extension],
        db_game: AsyncSurreal,
        **kwargs,
    ):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.enabled_extensions: list[Extension] = enabled_extensions
        self.db_game: AsyncSurreal = db_game

        super().__init__(*args, **kwargs)

    @override
    async def setup_hook(self) -> None:
        self.logger.info("Loading extensions...")
        for extension in self.enabled_extensions:
            try:
                await self.load_extension(name=extension.value)
            except Exception:
                self.logger.error(
                    f"Failed to load extension {extension.value}: {traceback.format_exc()}"
                )

    @override
    async def on_ready(self) -> None:
        self.logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        self.logger.info(f"Shard ID: {self.shard_id or 'N/A'}")
        self.logger.info(f"Shard Count: {self.shard_count or 'N/A'}")
        self.logger.info(f"Guild Count: {len(self.guilds)}")
        self.logger.info(f"User Count: {len(self.users)}")
        self.logger.info("Bot is ready!")
