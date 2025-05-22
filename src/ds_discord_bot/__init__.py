import asyncio
import logging
import logging.handlers
import os
import random

import discord
from dotenv import load_dotenv
from surrealdb import AsyncSurreal
from surrealdb.connections.async_ws import AsyncWsSurrealConnection

from .bot import DSBot
from .extensions import Extension

load_dotenv()
random.seed()

async def _async_main() -> None:
    log_level = os.getenv("DS_LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level)

    discord_logger = logging.getLogger("discord")
    discord_logger.setLevel(logging.INFO)

    ds_logger = logging.getLogger(__name__)
    ds_logger.setLevel(log_level)

    dt_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    discord_logger.addHandler(handler)
    ds_logger.addHandler(handler)

    ds_logger.info(
        f"Starting bot... {os.getenv('DS_DISCORD_TOKEN')[:5]}...{os.getenv('DS_DISCORD_TOKEN')[-5:]}"
    )

    db_game = AsyncSurreal(os.getenv("DS_SURREALDB_URL", "http://localhost:8000"))
    await db_game.signin(
        {
            "namespace": os.getenv("DS_SURREALDB_NAMESPACE", "ds_qu_shadows"),
            "username": os.getenv("DS_SURREALDB_USERNAME"),
            "password": os.getenv("DS_SURREALDB_PASSWORD"),
        }
    )
    await db_game.use(
        namespace=os.getenv("DS_SURREALDB_NAMESPACE", "ds_qu_shadows"),
        database="game",
    )

    try:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.moderation = True
        intents.members = True

        extensions = (
            [extension for extension in Extension]
            if not os.getenv("DS_EXTENSIONS")
            else [
                Extension[value.upper()]
                for value in os.getenv("DS_EXTENSIONS").split(",")
            ]
        )
        ds_logger.info(
            f"Enabled extensions: {', '.join([extension.name for extension in extensions])}"
        )

        async with DSBot(
            intents=intents,
            command_prefix=os.getenv("DS_DISCORD_COMMAND_PREFIX", "!"),
            case_insensitive=True,
            strip_after_prefix=True,
            description="Discord Game Server for Dystopia Sunset",
            enabled_extensions=extensions,
            db_game=db_game,
        ) as bot:
            await bot.start(token=os.getenv("DS_DISCORD_TOKEN"))
    except (KeyboardInterrupt, asyncio.CancelledError):
        ds_logger.info("Shutting down gracefully...")
    finally:
        if isinstance(db_game, AsyncWsSurrealConnection):
            ds_logger.info("Closing SurrealDB websocket connection...")
            await db_game.close()


def main():
    import asyncio

    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
