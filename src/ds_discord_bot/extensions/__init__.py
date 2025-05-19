from enum import Enum


class Extension(Enum):
    ADMIN = "ds_discord_bot.extensions.admin"
    GENERAL = "ds_discord_bot.extensions.general"
    MODERATION = "ds_discord_bot.extensions.moderation"
    WELCOME = "ds_discord_bot.extensions.welcome"
    PLAYER = "ds_discord_bot.extensions.player"
    CHARACTER = "ds_discord_bot.extensions.character"
    GAME = "ds_discord_bot.extensions.game"
