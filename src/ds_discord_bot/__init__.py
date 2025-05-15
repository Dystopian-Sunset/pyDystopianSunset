import asyncio
import os
import logging
import logging.handlers
import discord
from aiohttp import ClientSession
from dotenv import load_dotenv

from .bot import DSBot


load_dotenv()

async def _async_main() -> None:
    logger = logging.getLogger("discord")
    logger.setLevel(logging.INFO)

    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    async with ClientSession() as session:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.moderation = True
        intents.members = True

        async with DSBot(session=session, intents=intents, command_prefix="!") as bot:
            await bot.start(token=os.getenv("DS_DISCORD_TOKEN"))

def main():
    import asyncio
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()