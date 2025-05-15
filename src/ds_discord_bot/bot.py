import asyncio
from typing import override
import discord
from discord.ext import commands, tasks

class DSBot(commands.Bot):
    def __init__(self, *args,  **kwargs):
        super().__init__(*args, **kwargs)

    @override
    async def setup_hook(self) -> None:
        pass
