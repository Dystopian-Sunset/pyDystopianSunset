import random
from enum import Enum
from typing import ClassVar


class Theme(str, Enum):
    """Available name generation themes."""

    CYBERPUNK = "cyberpunk"
    FANTASY = "fantasy"
    WESTERN = "western"


class NameGenerator:
    # Cyberpunk noir-themed adjectives by letter
    cyberpunk_adjectives: ClassVar[dict[str, list[str]]] = {
        "a": [
            "augmented",
            "artificial",
            "android",
            "ashen",
            "analog",
            "aberrant",
            "archived",
        ],
        "b": ["binary", "black", "broken", "burned", "brazen", "biomodded", "bleeding"],
        "c": ["chrome", "cyber", "circuit", "corrupted", "cracked", "cold", "cryptic"],
        "d": ["digital", "dark", "distorted", "damaged", "dire", "dystopian", "dreary"],
        "e": [
            "electric",
            "encrypted",
            "eternal",
            "edgy",
            "enigmatic",
            "eerie",
            "enhanced",
        ],
        "f": [
            "fused",
            "fractured",
            "foggy",
            "fluorescent",
            "forgotten",
            "fragmented",
            "fatal",
        ],
        "g": ["glitched", "gritty", "ghost", "grim", "gunmetal", "gray", "glass"],
        "h": [
            "holographic",
            "haunted",
            "hardwired",
            "hacked",
            "hollow",
            "hostile",
            "hazed",
        ],
        "i": [
            "interconnected",
            "isolated",
            "implanted",
            "industrial",
            "icy",
            "illegal",
            "iron",
        ],
        "j": ["jacked", "jagged", "jaded", "jumbled", "jammed", "jarring", "jittery"],
        "k": ["kinetic", "killing", "keen", "karmic", "kinked", "kraken", "knifed"],
        "l": ["liquid", "lost", "lethal", "loud", "lurid", "laser", "lowlife"],
        "m": [
            "mechanical",
            "metallic",
            "misted",
            "modified",
            "masked",
            "monochrome",
            "midnight",
        ],
        "n": ["neon", "neural", "null", "noir", "nebulous", "noxious", "networked"],
        "o": [
            "obsolete",
            "overloaded",
            "obscured",
            "omni",
            "overclocked",
            "offline",
            "onyx",
        ],
        "p": ["polarized", "pixel", "phantom", "proxied", "primal", "pulse", "plasma"],
        "q": [
            "quantum",
            "quartz",
            "quicksilver",
            "questionable",
            "quarantined",
            "quiet",
            "quivering",
        ],
        "r": [
            "rogue",
            "rusted",
            "radioactive",
            "retro",
            "raining",
            "razored",
            "reflecting",
        ],
        "s": [
            "synthetic",
            "strobing",
            "steel",
            "shadowy",
            "static",
            "synced",
            "silent",
        ],
        "t": [
            "toxic",
            "terminal",
            "tungsten",
            "tarnished",
            "technological",
            "twisted",
            "tactical",
        ],
        "u": [
            "ultraviolet",
            "unstable",
            "uploaded",
            "urban",
            "unhinged",
            "underground",
            "unwired",
        ],
        "v": ["virtual", "void", "vaporized", "vacant", "viral", "vivid", "volatile"],
        "w": ["wired", "worn", "wasted", "wet", "warped", "watchful", "winter"],
        "x": ["xenon", "xerox", "xeno", "xtreme", "xplicit", "xcessively", "xotic"],
        "y": [
            "yellow",
            "yielding",
            "yearning",
            "yawning",
            "yellowed",
            "yesterdays",
            "yottabyte",
        ],
        "z": ["zealous", "zero", "zapped", "zoned", "zoomed", "zenith", "zigzag"],
    }

    # Cyberpunk noir-themed nouns by letter
    cyberpunk_nouns: ClassVar[dict[str, list[str]]] = {
        "a": [
            "alley",
            "artifact",
            "algorithm",
            "automaton",
            "augment",
            "archive",
            "android",
        ],
        "b": [
            "blade",
            "byte",
            "blackout",
            "borough",
            "bloodhound",
            "bulwark",
            "bunker",
        ],
        "c": ["circuit", "city", "codec", "construct", "chrome", "cyborg", "cortex"],
        "d": [
            "datastream",
            "detective",
            "district",
            "dashboard",
            "diesel",
            "domain",
            "drone",
        ],
        "e": ["enclave", "engine", "electrode", "enforcer", "edge", "enigma", "echo"],
        "f": [
            "framework",
            "fog",
            "firewall",
            "furnace",
            "fixer",
            "fragment",
            "frequency",
        ],
        "g": [
            "grid",
            "ghost",
            "gunslinger",
            "gateway",
            "glitch",
            "generator",
            "gearhead",
        ],
        "h": ["hivemind", "hacker", "harbor", "hologram", "highway", "heist", "hub"],
        "i": [
            "implant",
            "interface",
            "insurgent",
            "interceptor",
            "infiltrator",
            "injection",
            "impulse",
        ],
        "j": [
            "junkyard",
            "jacket",
            "junction",
            "junkie",
            "jukebox",
            "jammer",
            "jackpot",
        ],
        "k": [
            "killswitch",
            "kernel",
            "knockout",
            "kingpin",
            "knife",
            "kiosk",
            "keycode",
        ],
        "l": ["labyrinth", "laser", "lowlife", "looter", "lockdown", "lens", "ledger"],
        "m": [
            "mainframe",
            "mercenary",
            "matrix",
            "memory",
            "mechanic",
            "monolith",
            "maze",
        ],
        "n": ["network", "noir", "neuromancer", "needle", "nexus", "nightclub", "node"],
        "o": [
            "output",
            "operative",
            "overdrive",
            "outlaw",
            "override",
            "obelisk",
            "oracle",
        ],
        "p": ["port", "pulse", "phantom", "protocol", "precinct", "paradox", "proxy"],
        "q": [
            "quantum",
            "quarter",
            "quasar",
            "quarantine",
            "query",
            "quickdraw",
            "quark",
        ],
        "r": ["reactor", "runner", "rainstorm", "refugee", "resist", "router", "rift"],
        "s": [
            "syndicate",
            "shadows",
            "smuggler",
            "slums",
            "server",
            "synthetics",
            "streetrat",
        ],
        "t": [
            "terminal",
            "threshold",
            "transmitter",
            "tracker",
            "tether",
            "trance",
            "trenchcoat",
        ],
        "u": [
            "undercity",
            "uplink",
            "underworld",
            "utility",
            "uprising",
            "urbanite",
            "unit",
        ],
        "v": ["vector", "vault", "verge", "void", "vigilante", "voltage", "virus"],
        "w": [
            "wireframe",
            "wasteland",
            "wrapper",
            "warehouse",
            "wetware",
            "warden",
            "whisper",
        ],
        "x": [
            "xchange",
            "xenomorph",
            "xylograph",
            "xterminator",
            "xcavator",
            "xerogram",
            "xtension",
        ],
        "y": ["yards", "yield", "yottabyte", "youth", "yearning", "yesterday", "yoke"],
        "z": ["zone", "zero", "zapgun", "zenith", "zigzag", "zombie", "zealot"],
    }

    # Fantasy-themed adjectives by letter
    fantasy_adjectives: ClassVar[dict[str, list[str]]] = {
        "a": ["ancient", "arcane", "astral", "azure", "amber", "awakened", "ashen"],
        "b": ["blessed", "burning", "brave", "bronze", "bewitched", "brilliant", "broken"],
        "c": ["crystal", "cursed", "celestial", "crimson", "crowned", "cosmic", "cold"],
        "d": ["dark", "divine", "dragon", "dusk", "dire", "dream", "dwarven"],
        "e": ["elven", "enchanted", "eternal", "emerald", "ethereal", "epic", "elder"],
        "f": ["frozen", "fiery", "forgotten", "fabled", "forest", "fallen", "fey"],
        "g": ["golden", "ghost", "guardian", "grand", "grim", "gleaming", "granite"],
        "h": ["holy", "hidden", "haunted", "heroic", "hallowed", "highland", "hollow"],
        "i": ["iron", "ivory", "immortal", "infernal", "icy", "infinite", "island"],
        "j": ["jade", "jeweled", "just", "jungle", "jinxed", "jolly", "jagged"],
        "k": ["kindred", "kings", "knight", "keen", "kingdom", "karmic", "knightly"],
        "l": ["legendary", "lost", "lunar", "light", "living", "lofty", "loyal"],
        "m": ["mystic", "magical", "midnight", "misty", "mountain", "molten", "mighty"],
        "n": ["noble", "northern", "nether", "necro", "nightmare", "nomad", "nova"],
        "o": ["obsidian", "oracle", "onyx", "oath", "ocean", "omen", "oaken"],
        "p": ["phantom", "prismatic", "pure", "primal", "prophecy", "primeval", "peaceful"],
        "q": ["queens", "quest", "quartz", "quick", "quiet", "quaking", "questing"],
        "r": ["royal", "rune", "radiant", "raven", "ruby", "risen", "ridge"],
        "s": ["sacred", "silver", "shadow", "stellar", "scarlet", "stone", "spirit"],
        "t": ["twilight", "thunder", "timeless", "titan", "temple", "thorned", "true"],
        "u": ["undying", "umbral", "ultimate", "unicorn", "underground", "united", "unearthly"],
        "v": ["valiant", "violet", "void", "verdant", "vengeful", "valley", "viper"],
        "w": ["wandering", "wild", "white", "winter", "wondrous", "wise", "wicked"],
        "x": ["xeric", "xenolithic", "xerophyte", "xanadu", "xanthic", "xeric", "xystus"],
        "y": ["yielding", "yearning", "yonder", "youth", "yellow", "yew", "yawning"],
        "z": ["zealous", "zenith", "zephyr", "zodiac", "zone", "zealot", "zircon"],
    }

    # Fantasy-themed nouns by letter
    fantasy_nouns: ClassVar[dict[str, list[str]]] = {
        "a": ["altar", "amulet", "arrow", "axe", "abyss", "archway", "angel"],
        "b": ["blade", "bastion", "beast", "bridge", "bow", "banner", "beacon"],
        "c": ["castle", "crown", "crystal", "chalice", "cavern", "citadel", "crypt"],
        "d": ["dragon", "dagger", "dragon", "dungeon", "dawn", "defender", "depths"],
        "e": ["empire", "ember", "eclipse", "essence", "edge", "eagle", "elixir"],
        "f": ["forest", "flame", "fortress", "fang", "falcon", "fountain", "fate"],
        "g": ["guardian", "griffin", "gate", "grove", "gem", "glory", "golem"],
        "h": ["haven", "hammer", "herald", "heart", "helm", "hall", "horizon"],
        "i": ["isle", "iron", "ivory", "incantation", "inferno", "idol", "impact"],
        "j": ["jewel", "journey", "justice", "jade", "javelin", "jungle", "judgment"],
        "k": ["kingdom", "knight", "keep", "key", "king", "kinship", "kraken"],
        "l": ["lance", "light", "legend", "lantern", "lion", "lake", "lair"],
        "m": ["mountain", "mage", "magic", "moon", "mirror", "mist", "maze"],
        "n": ["nexus", "north", "night", "nexus", "nest", "nova", "needle"],
        "o": ["oracle", "oak", "oath", "order", "origin", "outcrop", "omega"],
        "p": ["peak", "phoenix", "portal", "palace", "prophecy", "path", "prism"],
        "q": ["quest", "queen", "quartz", "quarter", "quill", "quicksilver", "quasar"],
        "r": ["realm", "rune", "river", "ridge", "ring", "raven", "relic"],
        "s": ["sword", "star", "shield", "spell", "sanctuary", "spirit", "summit"],
        "t": ["temple", "throne", "tower", "talisman", "treasure", "titan", "torch"],
        "u": ["unicorn", "umbra", "unity", "uprising", "utopia", "underworld", "ultima"],
        "v": ["vale", "vault", "valley", "vigor", "vision", "vanguard", "virtue"],
        "w": ["wand", "wizard", "well", "wyrm", "watch", "willow", "ward"],
        "x": ["xanadu", "xerophyte", "xylem", "xenolith", "xebec", "xyst", "xiphoid"],
        "y": ["yew", "youth", "yesterday", "yonder", "yard", "yoke", "yearling"],
        "z": ["zenith", "zodiac", "zone", "zephyr", "zealot", "ziggurat", "zircon"],
    }

    # Western-themed adjectives by letter
    western_adjectives: ClassVar[dict[str, list[str]]] = {
        "a": ["aching", "arid", "armed", "angry", "aces", "ashen", "alone"],
        "b": ["blazing", "barren", "bloody", "brass", "broke", "bounty", "burning"],
        "c": ["crooked", "cactus", "copper", "canyon", "cattle", "crazy", "cold"],
        "d": ["dusty", "deadly", "desert", "drifting", "dry", "drawn", "daring"],
        "e": ["empty", "evening", "endless", "eight", "eager", "eastern", "echo"],
        "f": ["frontier", "faded", "fast", "fearless", "faithful", "forty", "fierce"],
        "g": ["gunslinger", "golden", "gravel", "gritty", "grizzled", "gambling", "ghost"],
        "h": ["hanging", "high", "hollow", "hired", "hidden", "howling", "hard"],
        "i": ["iron", "itching", "independence", "infamous", "inbound", "indian", "ivory"],
        "j": ["justice", "jagged", "jaded", "jackpot", "jumping", "jailed", "jawbone"],
        "k": ["killing", "kicking", "knifed", "keen", "kings", "kinked", "kansas"],
        "l": ["lonesome", "lawless", "leather", "lost", "loaded", "lightning", "last"],
        "m": ["mesa", "midnight", "marshal", "miner", "missing", "mountain", "moonlit"],
        "n": ["northern", "notorious", "nomad", "nevada", "native", "narrow", "noble"],
        "o": ["outlaw", "old", "open", "oracle", "october", "ominous", "owlhoot"],
        "p": ["prairie", "pistol", "painted", "phantom", "poker", "prospector", "pale"],
        "q": ["quick", "quarry", "quaking", "quiet", "queens", "quartered", "quartz"],
        "r": ["rugged", "renegade", "ranging", "rocky", "rustler", "riding", "rough"],
        "s": ["smoking", "stormy", "sunset", "shadow", "saddle", "savage", "silver"],
        "t": ["thunder", "tombstone", "tumbleweed", "trail", "texas", "trigger", "tarnished"],
        "u": ["unnamed", "untamed", "upstream", "urgency", "union", "ultimo", "unforgiven"],
        "v": ["vacant", "valley", "vigilante", "vulture", "vicious", "varmint", "vengeance"],
        "w": ["wild", "wanted", "weathered", "whiskey", "wandering", "wounded", "wagon"],
        "x": ["xeric", "xcut", "xpress", "xcavate", "xodus", "xtreme", "xhaust"],
        "y": ["yucca", "yellow", "yonder", "yearning", "yielding", "youth", "yokel"],
        "z": ["zephyr", "zealous", "zero", "zigzag", "zenith", "zone", "zorro"],
    }

    # Western-themed nouns by letter
    western_nouns: ClassVar[dict[str, list[str]]] = {
        "a": ["arrow", "axe", "ace", "ambush", "alamo", "anvil", "adobe"],
        "b": ["bronco", "bandit", "barrel", "bounty", "badge", "bullet", "bluff"],
        "c": ["canyon", "colt", "cattle", "cactus", "claim", "creek", "corral"],
        "d": ["drifter", "dealer", "dugout", "deputy", "draw", "desperado", "desert"],
        "e": ["express", "eagle", "edge", "expedition", "escape", "ember", "echo"],
        "f": ["forge", "frontier", "fork", "forty", "faro", "flats", "flint"],
        "g": ["gulch", "gambler", "gold", "grave", "gunfighter", "gang", "ghost"],
        "h": ["horseshoe", "homestead", "holler", "hanging", "highwayman", "holster", "hill"],
        "i": ["iron", "injun", "independence", "irons", "inquest", "inferno", "inkwell"],
        "j": ["judge", "jackpot", "jail", "junction", "justice", "jangle", "jerky"],
        "k": ["knife", "kick", "kingdom", "kingpin", "knot", "knoll", "kachina"],
        "l": ["lasso", "lawman", "lightning", "lode", "locomotive", "longhorn", "ledge"],
        "m": ["mustang", "mesa", "marshal", "mine", "maverick", "mission", "miner"],
        "n": ["noose", "nugget", "neck", "noon", "nomad", "notch", "needle"],
        "o": ["outlaw", "outpost", "outcrop", "oasis", "ox", "omen", "oro"],
        "p": ["posse", "pistol", "pony", "pass", "prairie", "poker", "prospector"],
        "q": ["quarry", "quickdraw", "quarter", "quartz", "quirt", "quest", "quarantine"],
        "r": ["ranch", "rustler", "rifle", "range", "rail", "ravine", "revolver"],
        "s": ["saloon", "sheriff", "spur", "saddle", "stagecoach", "snake", "sunset"],
        "t": ["trail", "tumbleweed", "trigger", "town", "territory", "trader", "tombstone"],
        "u": ["union", "uprising", "upstream", "undertaker", "ute", "urgency", "ultimo"],
        "v": ["valley", "vigilante", "vaquero", "varmint", "vista", "viper", "vengeance"],
        "w": ["wagon", "whiskey", "winchester", "wanted", "wells", "wrangler", "warden"],
        "x": ["xpress", "xchange", "xcavation", "xodus", "xpedition", "xroad", "xcelsior"],
        "y": ["yankee", "yucca", "yonder", "yard", "yokel", "yeoman", "yesterday"],
        "z": ["zigzag", "zone", "zenith", "zephyr", "zero", "zinc", "zorro"],
    }

    # Backward compatibility properties
    @property
    def adjectives(self) -> dict[str, list[str]]:
        """Backward compatibility: returns cyberpunk adjectives."""
        return self.cyberpunk_adjectives

    @property
    def nouns(self) -> dict[str, list[str]]:
        """Backward compatibility: returns cyberpunk nouns."""
        return self.cyberpunk_nouns

    @staticmethod
    def _get_word_lists(theme: Theme) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        """
        Get adjective and noun dictionaries for a given theme.

        Args:
            theme: Theme to get word lists for

        Returns:
            Tuple of (adjectives_dict, nouns_dict)
        """
        if theme == Theme.FANTASY:
            return NameGenerator.fantasy_adjectives, NameGenerator.fantasy_nouns
        elif theme == Theme.WESTERN:
            return NameGenerator.western_adjectives, NameGenerator.western_nouns
        else:  # Default to CYBERPUNK
            return NameGenerator.cyberpunk_adjectives, NameGenerator.cyberpunk_nouns

    @staticmethod
    def generate_name(theme: Theme = Theme.CYBERPUNK) -> str:
        """
        Generate a themed channel name with alliteration.

        Args:
            theme: Theme to use for name generation

        Returns:
            Generated name in format "adjective-noun"
        """
        adjectives, nouns = NameGenerator._get_word_lists(theme)

        # Choose a random letter for alliteration
        letter = random.choice(list("abcdefghijklmnopqrstuvwxyz"))

        # Check if the letter has both adjectives and nouns available
        if (
            letter in adjectives
            and letter in nouns
            and adjectives[letter]
            and nouns[letter]
        ):
            adj = random.choice(adjectives[letter])
            noun = random.choice(nouns[letter])
            return f"{adj}-{noun}"

        # Fallback in case a letter has no entries
        return NameGenerator.generate_name(theme)

    @staticmethod
    def generate_cyberpunk_channel_name() -> str:
        """
        Generate a cyberpunk-themed channel name.

        DEPRECATED: Use generate_name(Theme.CYBERPUNK) instead.

        Returns:
            Generated cyberpunk name in format "adjective-noun"
        """
        return NameGenerator.generate_name(Theme.CYBERPUNK)

    @staticmethod
    def generate_fantasy_name() -> str:
        """
        Generate a fantasy-themed name.

        Returns:
            Generated fantasy name in format "adjective-noun"
        """
        return NameGenerator.generate_name(Theme.FANTASY)

    @staticmethod
    def generate_western_name() -> str:
        """
        Generate a western-themed name.

        Returns:
            Generated western name in format "adjective-noun"
        """
        return NameGenerator.generate_name(Theme.WESTERN)

    @staticmethod
    def generate_multiple_names(count: int = 10, theme: Theme = Theme.CYBERPUNK) -> list[str]:
        """
        Generate multiple themed names.

        Args:
            count: Number of names to generate
            theme: Theme to use for all names

        Returns:
            List of generated names
        """
        return [NameGenerator.generate_name(theme) for _ in range(count)]
