import logging
import re

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


def clean_channel_name(name: str) -> str:
    # If channel name starts with non-alphanumeric or - characters, remove them
    name = re.sub(r"^[^a-zA-Z0-9-]+-", "", name)

    return name


async def find_category(
    bot: commands.Bot,
    name: str = "Speakeasy",
) -> discord.CategoryChannel | None:
    """
    Find the game session category
    """
    for category in bot.guilds[0].categories:
        if category.name == name:
            logger.debug(f"Found category {name}: {category}")
            return category

    logger.debug(f"Category {name} not found")
    return None


async def find_channel(
    bot: commands.Bot,
    name: str,
    category: discord.CategoryChannel | None = None,
) -> discord.TextChannel | None:
    """
    Find a channel by name
    """
    clean_name = clean_channel_name(name)

    if category:
        for channel in category.channels:
            if clean_channel_name(channel.name) == clean_name:
                logger.debug(f"Found channel {name}: {channel}")
                return channel
    else:
        for channel in bot.guilds[0].channels:
            if clean_channel_name(channel.name) == clean_name:
                logger.debug(f"Found channel {name}: {channel}")
                return channel

    logger.debug(f"Channel {name} not found")
    return None


async def create_text_channel(
    bot: commands.Bot,
    name: str,
    category: discord.CategoryChannel | None = None,
) -> discord.TextChannel | None:
    """
    Create a text channel in the game session category
    """
    if category:
        if not await find_channel(bot, name, category):
            channel = await category.create_text_channel(name)

            # Ensure channel is at bottom of category
            await channel.edit(position=len(category.channels) - 1)

            logger.debug(f"Created text channel: {name}")
            return channel
        else:
            logger.debug(f"Text channel already exists: {name}")
            return None

    logger.debug("Category not found, cannot create channel")
    return None


async def create_voice_channel(
    bot: commands.Bot,
    name: str,
    category: discord.CategoryChannel | None = None,
) -> discord.VoiceChannel | None:
    """
    Create a voice channel in the game session category
    """
    if category:
        if not await find_channel(bot, name, category):
            channel = await category.create_voice_channel(name)

            # Ensure channel is at bottom of category
            await channel.edit(position=len(category.channels) - 1)

            logger.debug(f"Created voice channel: {name}")
            return channel
        else:
            logger.debug(f"Voice channel already exists: {name}")
            return None

    logger.debug("Category not found, cannot create channel")
    return None


async def delete_channel(
    bot: commands.Bot,
    channel: str | discord.TextChannel | discord.VoiceChannel,
) -> bool:
    """
    Delete a channel in the game session category
    """
    if isinstance(channel, str):
        channel = await find_channel(bot, channel)

    if channel:
        await channel.delete()

        logger.debug(f"Deleted channel: {channel.name}")
        return True

    logger.debug("Channel not found, cannot delete channel")
    return False


async def move_member_to_voice_channel(
    bot: commands.Bot,
    member: discord.Member | discord.User,
    channel: discord.VoiceChannel | None = None,
    source_filter: str | None = None,
):
    if isinstance(member, discord.User):
        return

    if member.voice:
        if source_filter:
            if member.voice.channel != await find_channel(bot, source_filter):
                return

        if channel:
            if member.voice.channel != channel:
                return

        logger.debug(
            f"Moving member {member} from voice channel {member.voice.channel} to {channel}"
        )
        await member.move_to(channel)


async def send_dm(
    bot: commands.Bot,
    member: discord.Member | discord.User,
    message: str,
):
    if isinstance(member, discord.User):
        logger.debug(f"User {member} is not a member, cannot send DM")
        return

    if not member.dm_channel:
        await member.create_dm()

    try:
        await member.send(message)
    except discord.HTTPException:
        logger.warning(f"Failed to send DM to {member}")
