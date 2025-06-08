import random


class NameGenerator:
    # Cyberpunk noir-themed adjectives by letter
    adjectives = {
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
        "x": ["xenon", "xerox", "x-rated", "xeno", "xtreme", "xplicit", "xcessively"],
        "y": [
            "yellow",
            "yielding",
            "yearning",
            "yawning",
            "yellow-tinged",
            "yesterday's",
            "yottabyte",
        ],
        "z": ["zealous", "zero", "zapped", "zoned", "zoomed", "zenith", "zigzag"],
    }

    # Cyberpunk noir-themed nouns by letter
    nouns = {
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

    @staticmethod
    def generate_cyberpunk_channel_name() -> str:
        # Choose a random letter for alliteration
        letter = random.choice(list("abcdefghijklmnopqrstuvwxyz"))

        # Check if the letter has both adjectives and nouns available
        if (
            letter in NameGenerator.adjectives
            and letter in NameGenerator.nouns
            and NameGenerator.adjectives[letter]
            and NameGenerator.nouns[letter]
        ):
            adj = random.choice(NameGenerator.adjectives[letter])
            noun = random.choice(NameGenerator.nouns[letter])
            return f"{adj}-{noun}"
        else:
            # Fallback in case a letter has no entries
            return NameGenerator.generate_cyberpunk_channel_name()

    @staticmethod
    def generate_multiple_names(count=10) -> list[str]:
        return [NameGenerator.generate_cyberpunk_channel_name() for _ in range(count)]
