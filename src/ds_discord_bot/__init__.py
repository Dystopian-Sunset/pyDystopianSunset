import asyncio
import logging
import logging.handlers
import os
import random

import discord
from dotenv import load_dotenv

from ds_common.config_bot import get_config
from ds_common.metrics.service import get_metrics_service

from .bot import DSBot
from .extensions import Extension
from .metrics_server import MetricsServer
from .postgres_manager import PostgresManager

load_dotenv()
random.seed()


async def _async_main() -> None:
    # Load configuration (TOML + env overrides)
    config = get_config()

    log_level = getattr(logging, config.log_level.upper())

    # Configure root logger with the desired log level
    dt_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    # Set root logger level based on config
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)

    # Configure specific loggers with their desired levels
    websocket_logger = logging.getLogger("websockets")
    websocket_logger.setLevel(logging.WARNING)

    discord_logger = logging.getLogger("discord")
    discord_logger.setLevel(logging.INFO)

    ds_logger = logging.getLogger(__name__)
    ds_logger.setLevel(log_level)

    # Initialize metrics service
    metrics_service = get_metrics_service()
    metrics_service.set_bot_info(version="0.1.0")

    # Start metrics server if enabled
    metrics_server: MetricsServer | None = None
    if config.metrics_enabled:
        metrics_server = MetricsServer(host=config.metrics_host, port=config.metrics_port)
        metrics_server.start()
        ds_logger.info(f"Metrics server enabled on {config.metrics_host}:{config.metrics_port}")

    token = config.discord_token
    if token:
        ds_logger.info(f"Starting bot... {token[:5]}...{token[-5:]}")
    else:
        ds_logger.error("DS_DISCORD_TOKEN not set!")

    postgres_manager = await PostgresManager.create(
        host=config.postgres_host,
        port=config.postgres_port,
        database=config.postgres_database,
        user=config.postgres_user,
        password=config.postgres_password,
        pool_size=config.postgres_pool_size,
        max_overflow=config.postgres_max_overflow,
        echo=config.postgres_echo,
        read_replica_host=config.postgres_read_replica_host,
        read_replica_port=config.postgres_read_replica_port,
        read_replica_database=config.postgres_read_replica_database,
        read_replica_user=config.postgres_read_replica_user,
        read_replica_password=config.postgres_read_replica_password,
        read_replica_pool_size=config.postgres_read_replica_pool_size,
        read_replica_max_overflow=config.postgres_read_replica_max_overflow,
    )

    try:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.moderation = True
        intents.members = True

        extensions = (
            list(Extension)
            if not config.discord_extensions
            else [Extension[ext.upper()] for ext in config.discord_extensions]
        )
        ds_logger.info(
            f"Enabled extensions: {', '.join([extension.name for extension in extensions])}"
        )

        async with DSBot(
            intents=intents,
            command_prefix="!",
            case_insensitive=True,
            strip_after_prefix=True,
            description="Discord Game Server for Dystopia Sunset",
            enabled_extensions=extensions,
            postgres_manager=postgres_manager,
        ) as bot:
            await bot.start(token=token)
    except (KeyboardInterrupt, asyncio.CancelledError):
        ds_logger.info("Shutting down gracefully...")
    finally:
        # Stop metrics server
        if metrics_server:
            metrics_server.stop()


def main():
    import asyncio

    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
