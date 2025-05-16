from enum import Enum


class Extension(Enum):
    GENERAL = "ds_discord_bot.extensions.general"
    MODERATION = "ds_discord_bot.extensions.moderation"
    WELCOME = "ds_discord_bot.extensions.welcome"
    DISCORD_USER = "ds_discord_bot.extensions.discord_user"
    CHARACTER = "ds_discord_bot.extensions.character"
