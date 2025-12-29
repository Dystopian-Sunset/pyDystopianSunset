from discord import Color, Embed

from ds_common.combat.display import format_resource_display
from ds_common.config_bot import get_config
from ds_common.models.character import Character
from ds_common.models.character_class import CharacterClass


class CharacterWidget(Embed):
    def __init__(
        self,
        character: Character,
        character_class: CharacterClass,
        is_active: bool = False,
    ):
        super().__init__(color=Color.dark_blue() if is_active else Color.greyple())

        heading = f"{character.name} | lvl {character.level} | {character_class.name} | [N/A]" + (
            " (⭐)" if is_active else ""
        )

        # Format resources using the display utility (converts floats to ints)
        resources = format_resource_display(character)
        vitals = f"Health: {resources['current_health']}\nEnergy: {resources['current_tech_power']}\nExp: {character.exp}"
        stats = f"STR: {character.stats.get('STR', 0)}, DEX: {character.stats.get('DEX', 0)}, INT: {character.stats.get('INT', 0)}\nCHA: {character.stats.get('CHA', 0)}, PER: {character.stats.get('PER', 0)}, LUK: {character.stats.get('LUK', 0)}"
        fame = f"Renown: {character.renown}\nShadow Level: {character.shadow_level}"
        self.set_author(name=heading, icon_url="")
        self.add_field(name="Vitals", value=vitals, inline=True)
        self.add_field(name="Stats", value=stats, inline=True)
        self.add_field(name="Fame", value=fame)
        
        # Use configurable game name and subtitle
        config = get_config()
        game_name = config.game_name
        game_subtitle = config.game_subtitle
        
        if game_subtitle:
            footer_text = f"{game_name}: {game_subtitle}"
        else:
            footer_text = game_name
        
        self.set_footer(text=footer_text)
