"""
Theme system for location and POI generation.
"""

import random
from typing import Literal

ThemeCategory = Literal["visual", "atmosphere", "social", "economic"]

# Theme definitions by category
THEMES = {
    "visual": [
        "neon-lit",
        "industrial",
        "organic",
        "pristine",
        "rustic",
        "futuristic",
        "decaying",
        "gleaming",
        "shadowy",
        "luminous",
    ],
    "atmosphere": [
        "bustling",
        "quiet",
        "dangerous",
        "safe",
        "tense",
        "relaxed",
        "chaotic",
        "orderly",
        "mysterious",
        "welcoming",
    ],
    "social": [
        "corporate",
        "community",
        "transient",
        "insular",
        "open",
        "exclusive",
        "welcoming",
        "hostile",
        "neutral",
        "faction-controlled",
    ],
    "economic": [
        "luxury",
        "working-class",
        "impoverished",
        "mixed",
        "affluent",
        "modest",
        "elite",
        "common",
        "premium",
        "budget",
    ],
}

# City-specific theme profiles
CITY_THEMES = {
    "Neotopia": {
        "visual": ["neon-lit", "gleaming", "futuristic", "pristine"],
        "atmosphere": ["bustling", "orderly", "safe", "welcoming"],
        "social": ["corporate", "open", "welcoming", "neutral"],
        "economic": ["luxury", "affluent", "elite", "premium"],
    },
    "Agrihaven": {
        "visual": ["organic", "rustic", "natural", "pristine"],
        "atmosphere": ["quiet", "relaxed", "safe", "welcoming"],
        "social": ["community", "open", "welcoming", "neutral"],
        "economic": ["modest", "working-class", "common", "mixed"],
    },
    "Driftmark": {
        "visual": ["industrial", "rustic", "decaying", "shadowy"],
        "atmosphere": ["bustling", "tense", "chaotic", "mysterious"],
        "social": ["transient", "open", "neutral", "faction-controlled"],
        "economic": ["mixed", "working-class", "modest", "budget"],
    },
    "Skyward Nexus": {
        "visual": ["gleaming", "futuristic", "pristine", "luminous"],
        "atmosphere": ["quiet", "orderly", "safe", "exclusive"],
        "social": ["exclusive", "insular", "elite", "corporate"],
        "economic": ["luxury", "elite", "premium", "affluent"],
    },
    "The Undergrid": {
        "visual": ["industrial", "shadowy", "decaying", "rustic"],
        "atmosphere": ["dangerous", "tense", "chaotic", "mysterious"],
        "social": ["insular", "faction-controlled", "hostile", "neutral"],
        "economic": ["impoverished", "working-class", "budget", "modest"],
    },
}


def get_theme_for_city(city_name: str, category: ThemeCategory) -> str:
    """
    Get a theme for a specific city and category.

    Args:
        city_name: Name of the city
        category: Theme category

    Returns:
        Theme string
    """
    city_themes = CITY_THEMES.get(city_name, {})
    category_themes = city_themes.get(category, THEMES[category])
    return random.choice(category_themes)


def get_combined_theme(city_name: str) -> str:
    """
    Get a combined theme string for a city location.

    Args:
        city_name: Name of the city

    Returns:
        Combined theme string (e.g., "neon-lit corporate luxury")
    """
    visual = get_theme_for_city(city_name, "visual")
    social = get_theme_for_city(city_name, "social")
    economic = get_theme_for_city(city_name, "economic")

    return f"{visual} {social} {economic}"


def get_theme_for_poi_type(poi_type: str, city_name: str) -> str:
    """
    Get a theme for a specific POI type within a city.

    Args:
        poi_type: Type of POI (COMMERCIAL, ENTERTAINMENT, RESIDENTIAL, etc.)
        city_name: Name of the city

    Returns:
        Theme string
    """
    # Base theme on city
    base_theme = get_combined_theme(city_name)

    # Adjust based on POI type
    type_modifiers = {
        "COMMERCIAL": ["bustling", "welcoming"],
        "ENTERTAINMENT": ["lively", "energetic"],
        "RESIDENTIAL": ["quiet", "safe"],
        "INDUSTRIAL": ["gritty", "functional"],
        "PUBLIC": ["open", "accessible"],
        "SECRET": ["shadowy", "hidden"],
        "FACTION": ["controlled", "exclusive"],
    }

    modifier = random.choice(type_modifiers.get(poi_type, ["neutral"]))
    return f"{base_theme} {modifier}"
