"""
POI generator for procedural location creation.
"""

import random
from typing import Literal
from uuid import UUID

from ds_common.memory.location_graph_service import LocationGraphService
from ds_common.models.location_node import LocationNode
from ds_common.world_generation.theme_system import get_theme_for_poi_type

POIType = Literal[
    "COMMERCIAL",
    "ENTERTAINMENT",
    "RESIDENTIAL",
    "INDUSTRIAL",
    "PUBLIC",
    "SECRET",
    "FACTION",
]

# POI type distributions (percentages)
POI_DISTRIBUTIONS = {
    "COMMERCIAL": 0.30,
    "RESIDENTIAL": 0.20,
    "ENTERTAINMENT": 0.15,
    "INDUSTRIAL": 0.15,
    "PUBLIC": 0.10,
    "SECRET": 0.05,
    "FACTION": 0.05,
}

# POI name templates by type and city
POI_NAME_TEMPLATES = {
    "Neotopia": {
        "COMMERCIAL": [
            "{name} Weapon Emporium",
            "{name} Tech Store",
            "{name} Cyber Market",
            "{name} Quantum Shop",
            "{name} Neon Bazaar",
            "{name} Tech Repair",
            "{name} Data Broker",
            "{name} Augmentation Clinic",
        ],
        "ENTERTAINMENT": [
            "{name} Lounge",
            "{name} Club",
            "{name} Arcade",
            "{name} Theater",
            "{name} Bar",
            "{name} Casino",
            "{name} VR Parlor",
            "{name} Nightclub",
        ],
        "RESIDENTIAL": [
            "{name} Heights",
            "{name} Towers",
            "{name} Residences",
            "{name} Apartments",
            "{name} Complex",
            "{name} Suites",
            "{name} Living Quarters",
        ],
        "INDUSTRIAL": [
            "{name} Factory",
            "{name} Processing Plant",
            "{name} Manufacturing Hub",
            "{name} Assembly Line",
            "{name} Production Facility",
        ],
        "PUBLIC": [
            "{name} Plaza",
            "{name} Square",
            "{name} Park",
            "{name} Transit Hub",
            "{name} Station",
            "{name} Terminal",
        ],
        "SECRET": [
            "Hidden {name}",
            "Secret {name}",
            "Underground {name}",
            "Covert {name}",
        ],
        "FACTION": [
            "{faction} Headquarters",
            "{faction} Office",
            "{faction} Territory",
            "{faction} Base",
        ],
    },
    "Agrihaven": {
        "COMMERCIAL": [
            "{name} Market",
            "{name} General Store",
            "{name} Farm Supply",
            "{name} Trading Post",
            "{name} Harvest Shop",
        ],
        "ENTERTAINMENT": [
            "{name} Tavern",
            "{name} Inn",
            "{name} Gathering Hall",
            "{name} Festival Grounds",
        ],
        "RESIDENTIAL": [
            "{name} Farmstead",
            "{name} Community",
            "{name} Homestead",
            "{name} Village",
            "{name} Settlement",
        ],
        "INDUSTRIAL": [
            "{name} Processing Facility",
            "{name} Mill",
            "{name} Storage",
            "{name} Greenhouse",
            "{name} Barn",
        ],
        "PUBLIC": [
            "{name} Commons",
            "{name} Square",
            "{name} Market Square",
            "{name} Gathering Place",
        ],
        "SECRET": [
            "Hidden {name}",
            "Secret {name}",
        ],
        "FACTION": [
            "{faction} Territory",
            "{faction} Outpost",
        ],
    },
    "Driftmark": {
        "COMMERCIAL": [
            "{name} Trading Post",
            "{name} Port Market",
            "{name} Ship Supply",
            "{name} Harbor Shop",
            "{name} Cargo Exchange",
        ],
        "ENTERTAINMENT": [
            "{name} Tavern",
            "{name} Port Bar",
            "{name} Sailor's Rest",
            "{name} Harbor Inn",
        ],
        "RESIDENTIAL": [
            "{name} Quarters",
            "{name} Housing",
            "{name} Dockside",
            "{name} Portside",
        ],
        "INDUSTRIAL": [
            "{name} Warehouse",
            "{name} Cargo Bay",
            "{name} Shipyard",
            "{name} Dock",
        ],
        "PUBLIC": [
            "{name} Harbor",
            "{name} Dock",
            "{name} Port",
            "{name} Wharf",
        ],
        "SECRET": [
            "Hidden {name}",
            "Smuggler's {name}",
        ],
        "FACTION": [
            "{faction} Territory",
            "{faction} Hideout",
        ],
    },
    "Skyward Nexus": {
        "COMMERCIAL": [
            "{name} Boutique",
            "{name} Elite Shop",
            "{name} Sky Market",
            "{name} Premium Store",
        ],
        "ENTERTAINMENT": [
            "{name} Sky Lounge",
            "{name} Elite Club",
            "{name} Sky Bar",
            "{name} Aerial Theater",
        ],
        "RESIDENTIAL": [
            "{name} Sky Residences",
            "{name} Aerial Suites",
            "{name} Sky Towers",
            "{name} Elite Quarters",
        ],
        "INDUSTRIAL": [
            "{name} Sky Facility",
            "{name} Aerial Plant",
        ],
        "PUBLIC": [
            "{name} Sky Plaza",
            "{name} Aerial Terminal",
            "{name} Sky Station",
        ],
        "SECRET": [
            "Hidden {name}",
            "Exclusive {name}",
        ],
        "FACTION": [
            "{faction} Sky Office",
            "{faction} Aerial Base",
        ],
    },
    "The Undergrid": {
        "COMMERCIAL": [
            "{name} Shop",
            "{name} Market",
            "{name} Supply",
            "{name} Exchange",
        ],
        "ENTERTAINMENT": [
            "{name} Bar",
            "{name} Club",
            "{name} Den",
            "{name} Hideout",
        ],
        "RESIDENTIAL": [
            "{name} Housing Block",
            "{name} Quarters",
            "{name} Sector",
            "{name} Living Space",
        ],
        "INDUSTRIAL": [
            "{name} Plant",
            "{name} Facility",
            "{name} Maintenance",
            "{name} Generator",
        ],
        "PUBLIC": [
            "{name} Access",
            "{name} Hub",
            "{name} Junction",
        ],
        "SECRET": [
            "Hidden {name}",
            "Secret {name}",
            "Abandoned {name}",
        ],
        "FACTION": [
            "{faction} Territory",
            "{faction} Hideout",
            "{faction} Base",
        ],
    },
}

# POI description templates
POI_DESCRIPTION_TEMPLATES = {
    "COMMERCIAL": "A {theme} establishment where {activity}.",
    "ENTERTAINMENT": "A {theme} venue where {activity}.",
    "RESIDENTIAL": "A {theme} area where {activity}.",
    "INDUSTRIAL": "A {theme} facility where {activity}.",
    "PUBLIC": "A {theme} space where {activity}.",
    "SECRET": "A {theme} location where {activity}.",
    "FACTION": "A {theme} {faction} location where {activity}.",
}

# Atmosphere templates
ATMOSPHERE_TEMPLATES = {
    "COMMERCIAL": {
        "sights": ["neon signs", "display cases", "holographic advertisements"],
        "sounds": ["muffled conversations", "electronic beeps", "background music"],
        "smells": ["cleaning agents", "synthetic materials", "ozone"],
    },
    "ENTERTAINMENT": {
        "sights": ["dancing lights", "crowded spaces", "vibrant colors"],
        "sounds": ["loud music", "cheering", "clinking glasses"],
        "smells": ["alcohol", "perfume", "smoke"],
    },
    "RESIDENTIAL": {
        "sights": ["apartment buildings", "windows", "street lights"],
        "sounds": ["distant conversations", "mechanical hums", "footsteps"],
        "smells": ["cooking", "laundry", "urban air"],
    },
    "INDUSTRIAL": {
        "sights": ["machinery", "pipes", "industrial lighting"],
        "sounds": ["mechanical grinding", "steam hissing", "distant rumbling"],
        "smells": ["oil", "metal", "ozone"],
    },
    "PUBLIC": {
        "sights": ["open spaces", "people", "architecture"],
        "sounds": ["crowd noise", "footsteps", "ambient city sounds"],
        "smells": ["fresh air", "urban scents", "food vendors"],
    },
    "SECRET": {
        "sights": ["shadows", "hidden entrances", "dim lighting"],
        "sounds": ["echoes", "whispers", "distant sounds"],
        "smells": ["damp", "dust", "mystery"],
    },
    "FACTION": {
        "sights": ["faction symbols", "guarded entrances", "controlled spaces"],
        "sounds": ["guarded conversations", "security systems", "authority"],
        "smells": ["controlled environment", "power", "intimidation"],
    },
}


class POIGenerator:
    """
    Generator for Points of Interest (POIs).
    """

    def __init__(
        self,
        location_graph_service: LocationGraphService,
        city_name: str,
        city_node_id: UUID,
        poi_count: int,
    ):
        """
        Initialize the POI generator.

        Args:
            location_graph_service: Location graph service instance
            city_name: Name of the city/region
            city_node_id: Location node ID of the city
            poi_count: Number of POIs to generate
        """
        self.location_graph_service = location_graph_service
        self.city_name = city_name
        self.city_node_id = city_node_id
        self.poi_count = poi_count

    def _generate_poi_name(self, poi_type: POIType, name_parts: list[str]) -> str:
        """
        Generate a name for a POI.

        Args:
            poi_type: Type of POI
            name_parts: List of name parts to use

        Returns:
            Generated POI name
        """
        templates = POI_NAME_TEMPLATES.get(self.city_name, {}).get(poi_type, [])
        if not templates:
            templates = [f"{{name}} {poi_type}"]

        template = random.choice(templates)
        name = random.choice(name_parts)

        # Handle faction names if needed
        if "{faction}" in template:
            factions = [
                "Quillfangs",
                "Night Prowlers",
                "Slicktails",
                "Obsidian Beak Guild",
                "Serpent's Embrace",
                "Berserking Bruins",
            ]
            faction = random.choice(factions)
            return template.format(name=name, faction=faction)

        return template.format(name=name)

    def _generate_poi_description(self, poi_type: POIType, theme: str) -> str:
        """
        Generate a description for a POI.

        Args:
            poi_type: Type of POI
            theme: Theme string

        Returns:
            Generated description
        """
        activities = {
            "COMMERCIAL": [
                "merchants trade goods",
                "customers browse wares",
                "business is conducted",
            ],
            "ENTERTAINMENT": [
                "people gather for fun",
                "nightlife thrives",
                "entertainment is found",
            ],
            "RESIDENTIAL": ["residents live", "people call home", "communities exist"],
            "INDUSTRIAL": ["work is done", "production occurs", "industry operates"],
            "PUBLIC": ["people gather", "public life happens", "community meets"],
            "SECRET": ["secrets are kept", "hidden activities occur", "covert operations happen"],
            "FACTION": [
                "faction business is conducted",
                "faction members gather",
                "faction control is maintained",
            ],
        }

        activity = random.choice(activities.get(poi_type, ["activity occurs"]))
        template = POI_DESCRIPTION_TEMPLATES.get(poi_type, "A {theme} location where {activity}.")

        return template.format(theme=theme, activity=activity, faction="")

    def _generate_atmosphere(self, poi_type: POIType) -> dict:
        """
        Generate atmosphere details for a POI.

        Args:
            poi_type: Type of POI

        Returns:
            Atmosphere dictionary
        """
        base_atmosphere = ATMOSPHERE_TEMPLATES.get(
            poi_type,
            {
                "sights": ["various sights"],
                "sounds": ["various sounds"],
                "smells": ["various smells"],
            },
        )

        # Select 2-3 items from each category
        return {
            "sights": random.sample(
                base_atmosphere["sights"], min(3, len(base_atmosphere["sights"]))
            ),
            "sounds": random.sample(
                base_atmosphere["sounds"], min(3, len(base_atmosphere["sounds"]))
            ),
            "smells": random.sample(
                base_atmosphere["smells"], min(3, len(base_atmosphere["smells"]))
            ),
        }

    async def generate_pois(self) -> list[LocationNode]:
        """
        Generate all POIs for the city.

        Returns:
            List of created LocationNode instances
        """
        from ds_common.name_generator import NameGenerator

        generated_pois = []
        poi_counts = {}

        # Calculate POI counts by type
        for poi_type, percentage in POI_DISTRIBUTIONS.items():
            count = int(self.poi_count * percentage)
            poi_counts[poi_type] = count

        # Adjust for rounding
        total = sum(poi_counts.values())
        if total < self.poi_count:
            poi_counts["COMMERCIAL"] += self.poi_count - total

        # Generate name parts
        name_parts = []
        for _ in range(self.poi_count * 2):  # Generate extra names
            # Generate a name and extract a word from it
            name = NameGenerator.generate_cyberpunk_channel_name()
            # Use the noun part (after the hyphen) or the whole name
            if "-" in name:
                name_parts.append(name.split("-")[1].capitalize())
            else:
                name_parts.append(name.capitalize())

        # Generate POIs
        for poi_type, count in poi_counts.items():
            for _ in range(count):
                # Generate name
                poi_name = self._generate_poi_name(poi_type, name_parts)

                # Generate theme
                theme = get_theme_for_poi_type(poi_type, self.city_name)

                # Generate description
                description = self._generate_poi_description(poi_type, theme)

                # Generate atmosphere
                atmosphere = self._generate_atmosphere(poi_type)

                # Create location node
                location_node = await self.location_graph_service.create_location_node(
                    location_name=poi_name,
                    location_type="POI",
                    description=description,
                    atmosphere=atmosphere,
                    theme=theme,
                    parent_location_id=self.city_node_id,
                )

                generated_pois.append(location_node)

        return generated_pois
