from discord import Color, Embed

from ds_common.models.character import Character
from ds_common.models.character_class import CharacterClass

# Character Widget Layout
# -----------------------------------------------------
# | Char         | Character Name | Class Name | Level 
# | Avatar       |                |            |       
# -----------------------------------------------------
# | Faction | Shadow Level | Renown 
# -----------------------------------------------------
# | Stats:
# | Health
# | Stamina
# | 
# -----------------------------------------------------
# | Top Abilities:
# | 1)
# | 2)
# | 3)
# -----------------------------------------------------

class CharacterWidget(Embed):
    def __init__(self, character: Character, character_class: CharacterClass, is_active: bool = False):
        super().__init__(color=Color.dark_blue() if is_active else Color.greyple())

        heading = f"{character.name} | lvl {character.level} | {character_class.name} | [N/A]" + (" (⭐)" if is_active else "")
        vitals = f"Health: {character.stats['HP'] if "HP" in character.stats else 0}\nEnergy: {character.stats['ENG'] if "ENG" in character.stats else 0}"
        stats = f"STR: {character.stats['STR'] if "STR" in character.stats else 0}\nDEX: {character.stats['DEX'] if "DEX" in character.stats else 0}\nINT: {character.stats['INT'] if "INT" in character.stats else 0}\nCHA: {character.stats['CHA'] if "CHA" in character.stats else 0}\nPER: {character.stats['PER'] if "PER" in character.stats else 0}\nLUK: {character.stats['LUK'] if "LUK" in character.stats else 0}"
        fame = f"Renown: {character.renown}\nShadow Level: {character.shadow_level}"
        self.set_author(name=heading, icon_url="")
        self.add_field(name="Vitals", value=vitals, inline=True)
        self.add_field(name="Stats", value=stats, inline=True)
        self.add_field(name="Fame", value=fame)
        self.set_footer(text="Quillian Undercity: Shadows of the Syndicate")
