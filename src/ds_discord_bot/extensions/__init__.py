from enum import Enum


class Extension(Enum):
  GENERAL = "general"

AVAILABLE_EXTENSIONS = {
  Extension.GENERAL: "ds_discord_bot.extensions.general",
}