"""
World seed data for initializing the database with world regions, factions, calendar events, and baseline memories.
"""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

# Import all models to ensure SQLAlchemy can resolve relationships
from ds_common.models.calendar_event import CalendarEvent
from ds_common.models.calendar_month import CalendarMonth
from ds_common.models.location_fact import LocationFact
from ds_common.models.world_event import WorldEvent  # noqa: F401
from ds_common.models.world_item import WorldItem
from ds_common.models.world_memory import WorldMemory
from ds_common.models.world_region import WorldRegion

if TYPE_CHECKING:
    from ds_discord_bot.postgres_manager import PostgresManager

logger = logging.getLogger(__name__)

# World Regions seed data
WORLD_REGIONS = [
    # Cities
    {
        "id": UUID("00000000-0000-0000-0000-000000010001"),
        "name": "Neotopia",
        "region_type": "CITY",
        "description": "The gleaming technological utopia, a city of innovation and progress where the elite thrive.",
        "city": "Neotopia",
        "hierarchy_level": 0,
        "locations": [
            "Neotopia",
            "Neotopia Corporate Sector",
            "Neotopia Residential District",
            "Neotopia Tech Plaza",
        ],
        "factions": [],
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000010002"),
        "name": "The Undergrid",
        "region_type": "CITY",
        "description": "The underground infrastructure network beneath Neotopia, home to maintenance workers and the underworld.",
        "city": "The Undergrid",
        "hierarchy_level": 0,
        "locations": [
            "The Undergrid",
            "Undergrid Sector 7",
            "Undergrid Sector 12",
            "Undergrid Power Generation",
            "Undergrid Waste Management",
        ],
        "factions": [
            "Quillfangs",
            "Night Prowlers",
            "Slicktails",
            "Obsidian Beak Guild",
            "Serpent's Embrace",
            "Berserking Bruins",
        ],
    },
    # Neotopia Districts
    {
        "id": UUID("00000000-0000-0000-0000-000000010101"),
        "name": "Corporate Sector",
        "region_type": "DISTRICT",
        "description": "The business heart of Neotopia, where corporate powerhouses operate.",
        "city": "Neotopia",
        "parent_region_id": UUID("00000000-0000-0000-0000-000000010001"),
        "hierarchy_level": 1,
        "locations": ["Neotopia Corporate Sector"],
        "factions": [],
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000010102"),
        "name": "Residential District",
        "region_type": "DISTRICT",
        "description": "Where the citizens of Neotopia live, a mix of luxury and standard housing.",
        "city": "Neotopia",
        "parent_region_id": UUID("00000000-0000-0000-0000-000000010001"),
        "hierarchy_level": 1,
        "locations": ["Neotopia Residential District"],
        "factions": [],
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000010103"),
        "name": "Tech Plaza",
        "region_type": "DISTRICT",
        "description": "The technological hub of Neotopia, where innovation and research thrive.",
        "city": "Neotopia",
        "parent_region_id": UUID("00000000-0000-0000-0000-000000010001"),
        "hierarchy_level": 1,
        "locations": ["Neotopia Tech Plaza"],
        "factions": [],
    },
    # Undergrid Sectors
    {
        "id": UUID("00000000-0000-0000-0000-000000010201"),
        "name": "Sector 7",
        "region_type": "SECTOR",
        "description": "A maintenance sector in the Undergrid, known for worker activity.",
        "city": "The Undergrid",
        "parent_region_id": UUID("00000000-0000-0000-0000-000000010002"),
        "hierarchy_level": 2,
        "locations": ["Undergrid Sector 7"],
        "factions": ["Quillfangs"],
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000010202"),
        "name": "Sector 12",
        "region_type": "SECTOR",
        "description": "Another maintenance sector in the Undergrid.",
        "city": "The Undergrid",
        "parent_region_id": UUID("00000000-0000-0000-0000-000000010002"),
        "hierarchy_level": 2,
        "locations": ["Undergrid Sector 12"],
        "factions": ["Night Prowlers"],
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000010203"),
        "name": "Power Generation Sector",
        "region_type": "SECTOR",
        "description": "The power generation facilities of the Undergrid.",
        "city": "The Undergrid",
        "parent_region_id": UUID("00000000-0000-0000-0000-000000010002"),
        "hierarchy_level": 2,
        "locations": ["Undergrid Power Generation"],
        "factions": ["Berserking Bruins"],
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000010204"),
        "name": "Waste Management Sector",
        "region_type": "SECTOR",
        "description": "The waste management facilities of the Undergrid.",
        "city": "The Undergrid",
        "parent_region_id": UUID("00000000-0000-0000-0000-000000010002"),
        "hierarchy_level": 2,
        "locations": ["Undergrid Waste Management"],
        "factions": ["Slicktails", "Serpent's Embrace"],
    },
]

# Calendar Events seed data
CALENDAR_EVENTS = [
    {
        "id": UUID("00000000-0000-0000-0000-000000020001"),
        "name": "Spine Baroness Day",
        "event_type": "FACTION_CELEBRATION",
        "description": "A celebration honoring the Quillfangs leader, the Spine Baroness.",
        "start_game_time": {"year": None, "day": 200, "hour": 0},
        "end_game_time": {"year": None, "day": 200, "hour": 29},
        "is_recurring": True,
        "recurrence": {"pattern": "yearly"},
        "faction_specific": True,
        "affected_factions": ["Quillfangs"],
        "seasonal": False,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000020002"),
        "name": "Frostmane's Howl",
        "event_type": "FACTION_CELEBRATION",
        "description": "A Night Prowlers celebration honoring their pack leader, Garrick Frostmane.",
        "start_game_time": {"year": None, "day": 150, "hour": 0},
        "end_game_time": {"year": None, "day": 150, "hour": 29},
        "is_recurring": True,
        "recurrence": {"pattern": "yearly"},
        "faction_specific": True,
        "affected_factions": ["Night Prowlers"],
        "seasonal": False,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000020003"),
        "name": "Neotopia Tech Festival",
        "event_type": "FESTIVAL",
        "description": "A city-wide festival celebrating technological innovation in Neotopia.",
        "start_game_time": {"year": None, "day": 100, "hour": 0},
        "end_game_time": {"year": None, "day": 103, "hour": 29},
        "is_recurring": True,
        "recurrence": {"pattern": "yearly"},
        "faction_specific": False,
        "affected_factions": [],
        "seasonal": True,
        "regional_variations": {
            "Neotopia": {
                "name": "Neotopia Tech Festival",
                "description": "The grandest tech festival in the region.",
            },
            "The Undergrid": {
                "name": "Undergrid Tech Scavenge",
                "description": "A more subdued celebration in the underground.",
            },
        },
    },
]

# Baseline World Memories seed data
BASELINE_WORLD_MEMORIES = [
    {
        "id": UUID("00000000-0000-0000-0000-000000030001"),
        "memory_category": "location",
        "title": "Neotopia - The Technological Utopia",
        "description": "Neotopia is a gleaming city of innovation and progress, where technology and luxury coexist.",
        "full_narrative": "Neotopia stands as a beacon of technological advancement, a city where the elite thrive in luxury while the less fortunate struggle in the shadows. The city is divided into distinct districts: the Corporate Sector where business powerhouses operate, the Residential District where citizens live, and the Tech Plaza where innovation and research flourish. Beneath this utopian surface lies the Undergrid, a network of underground infrastructure where maintenance workers toil and the underworld factions operate.",
        "impact_level": "major",
        "is_public": True,
        "tags": ["neotopia", "city", "technology", "utopia"],
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000030002"),
        "memory_category": "location",
        "title": "The Undergrid - Underground Network",
        "description": "The underground infrastructure beneath Neotopia, home to maintenance workers and underworld factions.",
        "full_narrative": "The Undergrid is a vast network of tunnels, maintenance sectors, and infrastructure that runs beneath Neotopia. It is home to maintenance workers who keep the city running, but also serves as the base of operations for the various underworld factions. The Undergrid is divided into sectors, each with its own character and faction associations. Sector 7 is known for Quillfangs activity, Sector 12 for Night Prowlers, the Power Generation Sector for Berserking Bruins, and the Waste Management Sector for the Slicktails and Serpent's Embrace alliance.",
        "impact_level": "major",
        "is_public": True,
        "tags": ["undergrid", "underground", "infrastructure", "factions"],
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000030003"),
        "memory_category": "faction",
        "title": "Quillfangs - The Inclusive Strategists",
        "description": "The Quillfangs are known for their intelligence, versatility, and inclusive membership policy.",
        "full_narrative": "The Quillfangs, led by the Spine Baroness, are renowned for their intelligence and versatility. They excel in espionage, resource control, and strategic operations. What sets them apart is their inclusive membership policy - they embrace members from various species based on skills and unique traits, including humans on rare occasions. This diversity is viewed as a cornerstone of their success, allowing them to amass a diverse set of capabilities that enhance their adaptability and effectiveness.",
        "impact_level": "major",
        "is_public": True,
        "tags": ["quillfangs", "faction", "hedgehog", "spine baroness"],
        "related_entities": {"factions": ["Quillfangs"], "characters": []},
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000030004"),
        "memory_category": "faction",
        "title": "Night Prowlers - The Pack Loyalists",
        "description": "The Night Prowlers are a dominant force known for their strength, pack loyalty, and territorial nature.",
        "full_narrative": "The Night Prowlers, led by Garrick Frostmane, epitomize pack loyalty and strength. They are a dominant force in the underworld, often involved in territorial disputes. Their insularity ensures tight-knit cohesion and trust among members, which is vital for their survival and effectiveness. However, this also means they rarely form lasting alliances with other gangs, as their loyalty to the pack supersedes external affiliations.",
        "impact_level": "major",
        "is_public": True,
        "tags": ["night prowlers", "faction", "wolf", "garrick frostmane"],
        "related_entities": {"factions": ["Night Prowlers"], "characters": []},
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000030005"),
        "memory_category": "faction",
        "title": "Slicktails - Masters of Stealth",
        "description": "The Slicktails excel in covert operations, thievery, and stealth, led by Arletta Vixenblade.",
        "full_narrative": "The Slicktails, led by Arletta Vixenblade, are masters of stealth and thievery. They excel in covert operations, capable of stealing anything from valuable information to high-tech gadgets. They share a symbiotic relationship with the Serpent's Embrace, seamlessly blending their expertise to maximize their stealth and effectiveness in the shadows. This alliance allows them to complement each other's strengths, making them a formidable force in espionage and covert operations.",
        "impact_level": "major",
        "is_public": True,
        "tags": ["slicktails", "faction", "fox", "arletta vixenblade"],
        "related_entities": {"factions": ["Slicktails", "Serpent's Embrace"], "characters": []},
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000030006"),
        "memory_category": "faction",
        "title": "Obsidian Beak Guild - Intelligence Brokers",
        "description": "The Obsidian Beak Guild specializes in strategy, manipulation, and intelligence gathering, led by Corvin Blackfeather.",
        "full_narrative": "The Obsidian Beak Guild, led by Corvin Blackfeather, is characterized by their intellect and strategic thinking. They specialize in strategy and manipulation, often playing a long game to achieve their secretive goals. They leverage their unique attributes and skills to serve as the ultimate purveyors of intelligence and reconnaissance - for a price. They maintain a network of spies and informants across the underworld, using their knowledge to guide their clients and shape events to their advantage.",
        "impact_level": "major",
        "is_public": True,
        "tags": ["obsidian beak guild", "faction", "raven", "corvin blackfeather"],
        "related_entities": {"factions": ["Obsidian Beak Guild"], "characters": []},
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000030007"),
        "memory_category": "faction",
        "title": "Serpent's Embrace - Shadows of Death",
        "description": "The Serpent's Embrace are masters of stealth and assassination, known for their lethal precision.",
        "full_narrative": "The Serpent's Embrace, led by Sssilithra Coilborn, are known for their mastery in stealth and assassination. This clan is the embodiment of danger lurking in the shadows, with a reputation for their lethal precision in taking down targets. They share a symbiotic relationship with the Slicktails, seamlessly blending their expertise to maximize their stealth and effectiveness. Together, they form a formidable force in espionage and covert operations.",
        "impact_level": "major",
        "is_public": True,
        "tags": ["serpent's embrace", "faction", "snake", "sssilithra coilborn"],
        "related_entities": {"factions": ["Serpent's Embrace", "Slicktails"], "characters": []},
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000030008"),
        "memory_category": "faction",
        "title": "Berserking Bruins - The Powerhouse",
        "description": "The Berserking Bruins are known for their brute strength and formidable presence, led by Uldric Bearheart.",
        "full_narrative": "The Berserking Bruins, led by Uldric Bearheart, are brimming with brute strength and a formidable presence. They are the powerhouse of the underworld, often employed when sheer force is needed to resolve disputes or exert control. Their straightforward nature can make them predictable, limiting their potential for strategic alliances. Past interactions with the Night Prowlers have been characterized by brief periods of cooperation, driven by necessity rather than a genuine alignment of goals.",
        "impact_level": "major",
        "is_public": True,
        "tags": ["berserking bruins", "faction", "bear", "uldric bearheart"],
        "related_entities": {"factions": ["Berserking Bruins"], "characters": []},
    },
]

# Location Facts seed data
LOCATION_FACTS = [
    {
        "location_name": "Neotopia",
        "location_type": "CITY",
        "facts": [
            "Neotopia is a separate city from Agrihaven",
            "Agrihaven requires proper travel, not instant access",
            "Undergrid is beneath Neotopia",
            "Neotopia connects to Undergrid via access points",
            "Neotopia is a technological utopia",
            "Neotopia features gleaming spires and neon-lit streets",
            "The city is divided into Corporate Sector, Residential District, and Tech Plaza",
            "Neotopia is known for luxury, innovation, and corporate power",
            "Holographic displays and advanced technology are everywhere",
            "The city has efficient transit systems and sky-trains",
            "Neotopia's elite thrive in luxury while others struggle in shadows",
            "The city operates on a 24/7 schedule with minimal natural day/night cycles",
            "Corporate security and surveillance are extensive throughout the city",
            "Neotopia has climate-controlled environments and artificial weather systems",
        ],
        "connections": {
            "direct": ["The Undergrid"],
            "requires_travel": ["Agrihaven", "Driftmark", "Skyward Nexus"],
            "not_connected": [],
        },
        "travel_requirements": {
            "Agrihaven": {
                "method": "vehicle, transport lane, or scheduled cargo drone",
                "time": "several hours",
                "distance": "approximately 200 kilometers",
                "terrain": "urban sprawl, agricultural zones, rural-tech communities",
                "requirements": ["transportation", "proper route", "authorization for some routes"],
                "hazards": ["bandit activity in sprawl zones", "weather conditions", "checkpoints"],
                "cost": "transport fees vary by method, cargo drones are expensive",
                "description": "Travel to Agrihaven requires crossing the sprawl between cities. Options include cargo drones (quick but risky) or municipal transport shuttles (slower but safer).",
            },
            "Driftmark": {
                "method": "vehicle, transport lane, or maritime transport",
                "time": "several hours",
                "distance": "approximately 250 kilometers",
                "terrain": "coastal routes, port access, varied terrain",
                "requirements": ["transportation", "proper route"],
                "hazards": ["coastal weather", "port security", "maritime traffic"],
                "cost": "moderate transport fees",
                "description": "Driftmark is a port city accessible by land or sea transport. The journey takes several hours across varied terrain.",
            },
            "Skyward Nexus": {
                "method": "aerial transport or sky-bridge",
                "time": "several hours",
                "distance": "aerial distance varies",
                "terrain": "aerial routes, sky-bridges",
                "requirements": ["aerial transportation", "proper route", "elite authorization"],
                "hazards": ["aerial traffic control", "weather conditions", "security clearance"],
                "cost": "very expensive, elite-only access",
                "description": "Skyward Nexus is an elite aerial city. Access requires specialized aerial transport and often elite authorization.",
            },
        },
        "physical_properties": {
            "elevation": "sea level to elevated spires",
            "accessibility": "public transit, sky-trains, elevators, sky-bridges",
            "size": "vast metropolitan area spanning multiple districts",
            "architecture": "gleaming spires, neon-lit streets, holographic displays, glass and chrome",
            "climate": "climate-controlled, artificial weather systems, minimal natural elements",
            "lighting": "bright neon and holographic displays, minimal natural light, 24/7 illumination",
            "population_density": "high in corporate sector, moderate in residential, variable in tech plaza",
            "security_level": "high in corporate areas, moderate in residential, moderate in tech plaza",
            "atmosphere": "humming technology, distant sky-train sounds, holographic displays flickering, corporate announcements",
        },
        "constraints": {
            "cannot_reach_by": ["jump", "tunnel jump", "instant travel"],
            "requires": ["transportation for inter-city travel", "authorization for elite areas"],
            "forbidden_actions": [
                "flying without authorization",
                "unauthorized tunneling",
                "bypassing security checkpoints",
            ],
            "restrictions": [
                "curfew in some districts",
                "corporate security zones",
                "restricted airspace",
            ],
            "reason": "Cities are separate locations requiring proper travel",
        },
    },
    {
        "location_name": "Agrihaven",
        "location_type": "CITY",
        "facts": [
            "Agrihaven is a separate city from Neotopia",
            "Agrihaven is an agricultural haven",
            "Cannot be reached by jumping through tunnels",
            "Requires proper travel from Neotopia",
            "Agrihaven is not directly connected to the Undergrid",
            "Agrihaven features vast farmland and rural-tech communities",
            "The region is known for organic crops and bio-augmented flora",
            "Agrihaven has tight-knit communities and agricultural processing facilities",
            "The area is more rural and community-focused than Neotopia",
            "Travel to Agrihaven takes several hours by vehicle or transport",
            "Agrihaven cultivators are protective of their seed-rights and territory",
            "The region operates on natural day/night cycles and seasonal patterns",
            "Agrihaven has strong community governance and local traditions",
            "The area is known for its seed-rights protection and agricultural innovation",
        ],
        "connections": {
            "requires_travel": ["Neotopia", "Driftmark"],
            "not_connected": ["The Undergrid"],
        },
        "travel_requirements": {
            "Neotopia": {
                "method": "vehicle or transport",
                "time": "several hours",
                "distance": "approximately 200 kilometers",
                "terrain": "urban sprawl, agricultural zones, rural-tech communities",
                "requirements": ["transportation", "proper route"],
                "hazards": ["bandit activity in sprawl zones", "weather conditions", "checkpoints"],
                "cost": "moderate transport fees",
                "description": "Travel from Agrihaven to Neotopia requires crossing the sprawl. Transport shuttles are available but slower than cargo drones.",
            },
            "Driftmark": {
                "method": "vehicle or transport",
                "time": "several hours",
                "distance": "approximately 150 kilometers",
                "terrain": "agricultural zones, coastal routes",
                "requirements": ["transportation", "proper route"],
                "hazards": ["weather conditions", "rural checkpoints"],
                "cost": "moderate transport fees",
                "description": "Travel to Driftmark from Agrihaven takes several hours through agricultural and coastal terrain.",
            },
        },
        "physical_properties": {
            "elevation": "slightly above sea level, rolling terrain",
            "accessibility": "ground transport, rural roads, agricultural lanes",
            "size": "sprawling agricultural region with scattered communities",
            "architecture": "rural-tech buildings, agricultural processing facilities, community centers, traditional and modern mixed",
            "climate": "natural weather patterns, seasonal variations, agricultural climate control",
            "lighting": "natural daylight, minimal artificial lighting, community lighting in settlements",
            "population_density": "low, scattered communities, tight-knit settlements",
            "security_level": "moderate, community-based security, territorial protection",
            "atmosphere": "rustling crops, agricultural machinery, community sounds, natural wind",
        },
        "constraints": {
            "cannot_reach_by": ["jump", "tunnel jump", "instant travel", "walking from Undergrid"],
            "requires": [
                "transportation for inter-city travel",
                "respect for seed-rights and territory",
            ],
            "forbidden_actions": [
                "unauthorized access to agricultural zones",
                "seed theft",
                "territory violations",
            ],
            "restrictions": [
                "community curfews",
                "agricultural zone access",
                "seed-rights protection",
            ],
            "reason": "Agrihaven is a separate city that cannot be reached by jumping through tunnels or instant travel",
        },
    },
    {
        "location_name": "The Undergrid",
        "location_type": "CITY",
        "facts": [
            "The Undergrid is beneath Neotopia",
            "The Undergrid is not directly connected to other cities",
            "The Undergrid connects to Neotopia via access points",
            "Cannot reach other cities by jumping through tunnels from Undergrid",
            "The Undergrid is a network of tunnels, maintenance sectors, and infrastructure",
            "Geothermal power plants and maintenance facilities are located here",
            "The Undergrid is home to maintenance workers and underworld factions",
            "Access points include elevators, maintenance hatches, and service shafts",
            "The environment is gritty, industrial, and shadowy",
            "Sectors are divided by function: power generation, waste management, maintenance",
            "Faction territories exist throughout the Undergrid",
            "The Undergrid has poor ventilation and industrial hazards",
            "Maintenance workers keep the city above functioning",
            "The Undergrid operates 24/7 with shift workers",
        ],
        "connections": {
            "direct": ["Neotopia"],
            "requires_travel": [],
            "not_connected": ["Agrihaven", "Driftmark", "Skyward Nexus"],
        },
        "travel_requirements": {
            "Neotopia": {
                "method": "access point, elevator, or maintenance shaft",
                "time": "minutes",
                "distance": "vertical access, varies by location",
                "terrain": "vertical shafts, maintenance corridors, access tunnels",
                "requirements": ["access point", "authorization for official routes"],
                "hazards": [
                    "industrial hazards",
                    "poor ventilation",
                    "faction territories",
                    "security patrols",
                ],
                "cost": "free for workers, varies for unauthorized access",
                "description": "The Undergrid connects to Neotopia via multiple access points including elevators, maintenance hatches, and service shafts. Official routes require authorization, but unofficial routes exist.",
            },
        },
        "physical_properties": {
            "elevation": "underground, varying depths beneath Neotopia",
            "accessibility": "elevators, maintenance hatches, service shafts, tunnel networks",
            "size": "vast underground network spanning beneath entire city",
            "architecture": "industrial tunnels, concrete and metal, maintenance facilities, geothermal plants",
            "climate": "warm from geothermal systems, poor ventilation, industrial air quality",
            "lighting": "dim industrial lighting, flickering lights, emergency lighting, minimal natural light",
            "population_density": "moderate, concentrated in sectors, workers and faction members",
            "security_level": "low in most areas, faction-controlled territories, minimal official security",
            "atmosphere": "stale air, humming machinery, echoing footsteps, distant maintenance work, industrial sounds",
        },
        "constraints": {
            "cannot_reach_by": ["jump to other cities", "tunnel jump to cities"],
            "requires": [
                "access points for Neotopia",
                "knowledge of tunnel networks for navigation",
            ],
            "forbidden_actions": [
                "unauthorized access to power facilities",
                "interfering with critical infrastructure",
            ],
            "restrictions": [
                "faction territories",
                "restricted maintenance zones",
                "geothermal plant security",
            ],
            "reason": "The Undergrid is beneath Neotopia and not connected to other cities",
        },
    },
    {
        "location_name": "Undergrid Sector 7",
        "location_type": "SECTOR",
        "facts": [
            "Sector 7 is within the Undergrid",
            "Sector 7 is accessible from other Undergrid sectors",
            "Sector 7 is not directly connected to cities outside the Undergrid",
            "Sector 7 is Quillfangs territory",
            "Sector 7 contains maintenance workshops and storage facilities",
            "The sector has poor ventilation and industrial hazards",
            "Access to Sector 7 requires passing through main Undergrid corridors",
            "Sector 7 workers are known for their technical expertise",
            "The sector is a hub for maintenance operations and equipment storage",
            "Quillfangs maintain influence and control in Sector 7",
        ],
        "connections": {
            "direct": ["The Undergrid", "Undergrid Sector 12"],
            "requires_travel": [],
            "not_connected": ["Agrihaven", "Neotopia", "Driftmark", "Skyward Nexus"],
        },
        "travel_requirements": {
            "The Undergrid": {
                "method": "tunnel network, maintenance corridors",
                "time": "minutes",
                "distance": "within Undergrid network",
                "terrain": "maintenance tunnels, corridors",
                "requirements": ["knowledge of tunnel network", "access to Undergrid"],
                "hazards": ["poor ventilation", "industrial hazards", "Quillfangs presence"],
                "cost": "free for workers, may require faction permission",
                "description": "Sector 7 is accessible through the main Undergrid tunnel network. Travel is quick but requires navigating maintenance corridors.",
            },
        },
        "physical_properties": {
            "elevation": "underground, beneath Neotopia",
            "accessibility": "maintenance corridors, tunnel network",
            "size": "moderate sector size, multiple workshops and storage areas",
            "architecture": "industrial workshops, storage facilities, maintenance equipment, concrete and metal",
            "climate": "warm from industrial activity, poor ventilation, industrial air",
            "lighting": "dim industrial lighting, workshop lights, flickering emergency lights",
            "population_density": "moderate, workers and Quillfangs members",
            "security_level": "low official security, Quillfangs-controlled territory",
            "atmosphere": "workshop sounds, machinery humming, echoing voices, industrial smells, Quillfangs activity",
        },
        "constraints": {
            "cannot_reach_by": ["jump to cities", "direct access from Neotopia without Undergrid"],
            "requires": ["access through Undergrid", "awareness of Quillfangs territory"],
            "forbidden_actions": [
                "interfering with Quillfangs operations",
                "unauthorized equipment access",
            ],
            "restrictions": [
                "Quillfangs territory",
                "maintenance zone access",
                "equipment storage security",
            ],
            "reason": "Sector 7 is within the Undergrid and requires proper access through tunnel networks",
        },
    },
    {
        "location_name": "Neotopia Corporate Sector",
        "location_type": "DISTRICT",
        "facts": [
            "Corporate Sector is within Neotopia",
            "Corporate Sector is accessible from other Neotopia districts",
            "Corporate Sector houses major business headquarters",
            "The area has high security and surveillance",
            "Corporate Sector is connected to sky-train network",
            "The sector features luxury amenities for corporate elite",
            "Access to some buildings requires corporate authorization",
            "Corporate Sector is the business heart of Neotopia",
            "The sector operates on a 24/7 business schedule",
            "Corporate powerhouses and financial institutions are located here",
        ],
        "connections": {
            "direct": ["Neotopia", "Neotopia Residential District", "Neotopia Tech Plaza"],
            "requires_travel": [],
        },
        "travel_requirements": {
            "Neotopia Residential District": {
                "method": "sky-train, walking, transit",
                "time": "minutes",
                "distance": "within Neotopia",
                "terrain": "urban streets, sky-train network",
                "requirements": ["public transit access"],
                "hazards": ["minimal, well-secured area"],
                "cost": "public transit fees",
                "description": "The Corporate Sector is directly connected to other Neotopia districts via sky-train and transit systems.",
            },
            "Neotopia Tech Plaza": {
                "method": "sky-train, walking, transit",
                "time": "minutes",
                "distance": "within Neotopia",
                "terrain": "urban streets, sky-train network",
                "requirements": ["public transit access"],
                "hazards": ["minimal, well-secured area"],
                "cost": "public transit fees",
                "description": "The Corporate Sector is directly connected to Tech Plaza via sky-train and transit systems.",
            },
        },
        "physical_properties": {
            "elevation": "ground level to elevated corporate towers",
            "accessibility": "sky-train network, public transit, elevators, sky-bridges",
            "size": "large district with multiple corporate complexes",
            "architecture": "gleaming corporate towers, glass and chrome, luxury amenities, holographic displays",
            "climate": "climate-controlled, artificial weather, perfect conditions",
            "lighting": "bright corporate lighting, holographic displays, 24/7 illumination",
            "population_density": "high during business hours, moderate off-hours",
            "security_level": "very high, extensive surveillance, corporate security",
            "atmosphere": "hushed corporate activity, distant sky-train sounds, holographic displays, corporate announcements",
        },
        "constraints": {
            "cannot_reach_by": ["unauthorized access", "bypassing security"],
            "requires": [
                "public transit for district access",
                "corporate authorization for some buildings",
            ],
            "forbidden_actions": [
                "unauthorized building access",
                "bypassing security systems",
                "corporate espionage",
            ],
            "restrictions": [
                "corporate security zones",
                "restricted building access",
                "surveillance areas",
            ],
            "reason": "Corporate Sector has high security and requires proper access methods",
        },
    },
    {
        "location_name": "Neotopia Residential District",
        "location_type": "DISTRICT",
        "facts": [
            "Residential District is within Neotopia",
            "Residential District is accessible from other Neotopia districts",
            "The district is where citizens of Neotopia live",
            "Mix of luxury and standard housing",
            "The area has a mix of socioeconomic levels",
            "Residential District is connected to sky-train network",
            "The district features residential complexes and community spaces",
            "Access is generally open to Neotopia residents",
            "The area operates on natural day/night cycles with some artificial lighting",
            "Residential District has moderate security compared to Corporate Sector",
        ],
        "connections": {
            "direct": ["Neotopia", "Neotopia Corporate Sector", "Neotopia Tech Plaza"],
            "requires_travel": [],
        },
        "travel_requirements": {
            "Neotopia Corporate Sector": {
                "method": "sky-train, walking, transit",
                "time": "minutes",
                "distance": "within Neotopia",
                "terrain": "urban streets, sky-train network",
                "requirements": ["public transit access"],
                "hazards": ["minimal, well-secured area"],
                "cost": "public transit fees",
                "description": "The Residential District is directly connected to Corporate Sector via sky-train and transit systems.",
            },
            "Neotopia Tech Plaza": {
                "method": "sky-train, walking, transit",
                "time": "minutes",
                "distance": "within Neotopia",
                "terrain": "urban streets, sky-train network",
                "requirements": ["public transit access"],
                "hazards": ["minimal, well-secured area"],
                "cost": "public transit fees",
                "description": "The Residential District is directly connected to Tech Plaza via sky-train and transit systems.",
            },
        },
        "physical_properties": {
            "elevation": "ground level to mid-rise residential buildings",
            "accessibility": "sky-train network, public transit, walking paths",
            "size": "large residential district with varied housing",
            "architecture": "residential complexes, mixed luxury and standard housing, community spaces",
            "climate": "climate-controlled, natural day/night cycles, comfortable conditions",
            "lighting": "natural daylight, residential lighting, moderate artificial lighting",
            "population_density": "high, residential area with active community life",
            "security_level": "moderate, residential security, community watch",
            "atmosphere": "residential activity, community sounds, sky-train in distance, daily life",
        },
        "constraints": {
            "cannot_reach_by": ["unauthorized access to private residences"],
            "requires": [
                "public transit for district access",
                "residence authorization for private areas",
            ],
            "forbidden_actions": [
                "unauthorized residence access",
                "trespassing",
                "residential violations",
            ],
            "restrictions": ["private residence access", "community curfews in some areas"],
            "reason": "Residential District requires proper access and respect for private residences",
        },
    },
    {
        "location_name": "Neotopia Tech Plaza",
        "location_type": "DISTRICT",
        "facts": [
            "Tech Plaza is within Neotopia",
            "Tech Plaza is accessible from other Neotopia districts",
            "Tech Plaza is the technological hub of Neotopia",
            "The area is where innovation and research thrive",
            "Tech Plaza houses research facilities and tech companies",
            "The district is connected to sky-train network",
            "Tech Plaza features cutting-edge technology and innovation centers",
            "Access to some facilities requires tech authorization",
            "The area operates on a flexible schedule for research and development",
            "Tech Plaza is known for experimental technology and breakthrough innovations",
        ],
        "connections": {
            "direct": ["Neotopia", "Neotopia Corporate Sector", "Neotopia Residential District"],
            "requires_travel": [],
        },
        "travel_requirements": {
            "Neotopia Corporate Sector": {
                "method": "sky-train, walking, transit",
                "time": "minutes",
                "distance": "within Neotopia",
                "terrain": "urban streets, sky-train network",
                "requirements": ["public transit access"],
                "hazards": ["minimal, well-secured area"],
                "cost": "public transit fees",
                "description": "Tech Plaza is directly connected to Corporate Sector via sky-train and transit systems.",
            },
            "Neotopia Residential District": {
                "method": "sky-train, walking, transit",
                "time": "minutes",
                "distance": "within Neotopia",
                "terrain": "urban streets, sky-train network",
                "requirements": ["public transit access"],
                "hazards": ["minimal, well-secured area"],
                "cost": "public transit fees",
                "description": "Tech Plaza is directly connected to Residential District via sky-train and transit systems.",
            },
        },
        "physical_properties": {
            "elevation": "ground level to research towers",
            "accessibility": "sky-train network, public transit, research facilities",
            "size": "moderate district with research complexes and innovation centers",
            "architecture": "modern research facilities, tech innovation centers, experimental architecture",
            "climate": "climate-controlled, research-grade environmental conditions",
            "lighting": "bright research lighting, holographic displays, experimental lighting systems",
            "population_density": "moderate, researchers and tech workers",
            "security_level": "high for research facilities, moderate for public areas",
            "atmosphere": "humming technology, research activity, experimental sounds, innovation buzz",
        },
        "constraints": {
            "cannot_reach_by": ["unauthorized access to research facilities"],
            "requires": [
                "public transit for district access",
                "tech authorization for research facilities",
            ],
            "forbidden_actions": [
                "unauthorized research facility access",
                "technology theft",
                "research interference",
            ],
            "restrictions": [
                "research facility access",
                "experimental technology zones",
                "intellectual property protection",
            ],
            "reason": "Tech Plaza has high security for research facilities and requires proper authorization",
        },
    },
    {
        "location_name": "Undergrid Sector 12",
        "location_type": "SECTOR",
        "facts": [
            "Sector 12 is within the Undergrid",
            "Sector 12 is accessible from other Undergrid sectors",
            "Sector 12 is not directly connected to cities outside the Undergrid",
            "Sector 12 is Night Prowlers territory",
            "Sector 12 contains maintenance facilities and storage areas",
            "The sector has poor ventilation and industrial hazards",
            "Access to Sector 12 requires passing through main Undergrid corridors",
            "Sector 12 workers maintain critical infrastructure",
            "The sector is a hub for maintenance operations",
            "Night Prowlers maintain strong territorial control in Sector 12",
        ],
        "connections": {
            "direct": ["The Undergrid", "Undergrid Sector 7"],
            "requires_travel": [],
            "not_connected": ["Agrihaven", "Neotopia", "Driftmark", "Skyward Nexus"],
        },
        "travel_requirements": {
            "The Undergrid": {
                "method": "tunnel network, maintenance corridors",
                "time": "minutes",
                "distance": "within Undergrid network",
                "terrain": "maintenance tunnels, corridors",
                "requirements": ["knowledge of tunnel network", "access to Undergrid"],
                "hazards": ["poor ventilation", "industrial hazards", "Night Prowlers presence"],
                "cost": "free for workers, may require faction permission",
                "description": "Sector 12 is accessible through the main Undergrid tunnel network. Travel is quick but requires navigating maintenance corridors and Night Prowlers territory.",
            },
        },
        "physical_properties": {
            "elevation": "underground, beneath Neotopia",
            "accessibility": "maintenance corridors, tunnel network",
            "size": "moderate sector size, multiple maintenance facilities",
            "architecture": "industrial maintenance facilities, storage areas, concrete and metal",
            "climate": "warm from industrial activity, poor ventilation, industrial air",
            "lighting": "dim industrial lighting, maintenance lights, flickering emergency lights",
            "population_density": "moderate, workers and Night Prowlers members",
            "security_level": "low official security, Night Prowlers-controlled territory",
            "atmosphere": "maintenance sounds, machinery humming, territorial presence, industrial smells, Night Prowlers activity",
        },
        "constraints": {
            "cannot_reach_by": ["jump to cities", "direct access from Neotopia without Undergrid"],
            "requires": ["access through Undergrid", "awareness of Night Prowlers territory"],
            "forbidden_actions": [
                "interfering with Night Prowlers operations",
                "territorial violations",
            ],
            "restrictions": [
                "Night Prowlers territory",
                "maintenance zone access",
                "territorial boundaries",
            ],
            "reason": "Sector 12 is within the Undergrid and requires proper access through tunnel networks, with Night Prowlers territorial control",
        },
    },
    {
        "location_name": "Undergrid Power Generation",
        "location_type": "SECTOR",
        "facts": [
            "Power Generation Sector is within the Undergrid",
            "Power Generation Sector is accessible from other Undergrid sectors",
            "Power Generation Sector is not directly connected to cities outside the Undergrid",
            "Power Generation Sector is Berserking Bruins territory",
            "The sector contains geothermal power plants and energy facilities",
            "The sector has extreme heat and industrial hazards",
            "Access to Power Generation requires passing through main Undergrid corridors",
            "Power Generation workers maintain critical energy infrastructure",
            "The sector is essential for powering Neotopia above",
            "Berserking Bruins maintain control over power generation facilities",
        ],
        "connections": {
            "direct": ["The Undergrid"],
            "requires_travel": [],
            "not_connected": ["Agrihaven", "Neotopia", "Driftmark", "Skyward Nexus"],
        },
        "travel_requirements": {
            "The Undergrid": {
                "method": "tunnel network, maintenance corridors",
                "time": "minutes",
                "distance": "within Undergrid network",
                "terrain": "maintenance tunnels, power facility corridors",
                "requirements": [
                    "knowledge of tunnel network",
                    "access to Undergrid",
                    "safety equipment for power facilities",
                ],
                "hazards": [
                    "extreme heat",
                    "industrial hazards",
                    "power facility dangers",
                    "Berserking Bruins presence",
                ],
                "cost": "free for workers, may require faction permission",
                "description": "Power Generation Sector is accessible through the main Undergrid tunnel network. The area has extreme heat and industrial hazards, requiring proper safety equipment.",
            },
        },
        "physical_properties": {
            "elevation": "underground, beneath Neotopia",
            "accessibility": "maintenance corridors, tunnel network, power facility access",
            "size": "large sector with extensive power generation facilities",
            "architecture": "geothermal power plants, energy facilities, industrial infrastructure, concrete and metal",
            "climate": "extremely hot from geothermal activity, poor ventilation, intense industrial heat",
            "lighting": "bright industrial lighting, power facility lights, intense heat glow",
            "population_density": "low to moderate, power workers and Berserking Bruins members",
            "security_level": "moderate for power facilities, Berserking Bruins-controlled territory",
            "atmosphere": "roaring geothermal activity, intense heat, power generation sounds, industrial intensity, Berserking Bruins presence",
        },
        "constraints": {
            "cannot_reach_by": ["jump to cities", "direct access from Neotopia without Undergrid"],
            "requires": [
                "access through Undergrid",
                "safety equipment",
                "awareness of Berserking Bruins territory",
            ],
            "forbidden_actions": [
                "interfering with power generation",
                "unauthorized facility access",
                "sabotage",
            ],
            "restrictions": [
                "power facility access",
                "Berserking Bruins territory",
                "critical infrastructure security",
            ],
            "reason": "Power Generation Sector is within the Undergrid and requires proper access through tunnel networks, with critical infrastructure and Berserking Bruins control",
        },
    },
    {
        "location_name": "Undergrid Waste Management",
        "location_type": "SECTOR",
        "facts": [
            "Waste Management Sector is within the Undergrid",
            "Waste Management Sector is accessible from other Undergrid sectors",
            "Waste Management Sector is not directly connected to cities outside the Undergrid",
            "Waste Management Sector is Slicktails and Serpent's Embrace territory",
            "The sector contains waste processing facilities and disposal systems",
            "The sector has poor air quality and industrial hazards",
            "Access to Waste Management requires passing through main Undergrid corridors",
            "Waste Management workers process Neotopia's waste",
            "The sector is essential for maintaining city sanitation",
            "Slicktails and Serpent's Embrace share control over waste management facilities",
        ],
        "connections": {
            "direct": ["The Undergrid"],
            "requires_travel": [],
            "not_connected": ["Agrihaven", "Neotopia", "Driftmark", "Skyward Nexus"],
        },
        "travel_requirements": {
            "The Undergrid": {
                "method": "tunnel network, maintenance corridors",
                "time": "minutes",
                "distance": "within Undergrid network",
                "terrain": "maintenance tunnels, waste facility corridors",
                "requirements": [
                    "knowledge of tunnel network",
                    "access to Undergrid",
                    "protective equipment for waste facilities",
                ],
                "hazards": [
                    "poor air quality",
                    "industrial hazards",
                    "waste processing dangers",
                    "Slicktails and Serpent's Embrace presence",
                ],
                "cost": "free for workers, may require faction permission",
                "description": "Waste Management Sector is accessible through the main Undergrid tunnel network. The area has poor air quality and industrial hazards, requiring protective equipment.",
            },
        },
        "physical_properties": {
            "elevation": "underground, beneath Neotopia",
            "accessibility": "maintenance corridors, tunnel network, waste facility access",
            "size": "large sector with extensive waste processing facilities",
            "architecture": "waste processing plants, disposal systems, industrial infrastructure, concrete and metal",
            "climate": "warm from waste processing, poor ventilation, industrial air quality",
            "lighting": "dim industrial lighting, waste facility lights, minimal natural light",
            "population_density": "low to moderate, waste workers and faction members",
            "security_level": "low official security, Slicktails and Serpent's Embrace-controlled territory",
            "atmosphere": "waste processing sounds, industrial activity, poor air quality, faction presence, shadowy operations",
        },
        "constraints": {
            "cannot_reach_by": ["jump to cities", "direct access from Neotopia without Undergrid"],
            "requires": [
                "access through Undergrid",
                "protective equipment",
                "awareness of faction territories",
            ],
            "forbidden_actions": [
                "interfering with waste processing",
                "unauthorized facility access",
                "territorial violations",
            ],
            "restrictions": [
                "waste facility access",
                "Slicktails and Serpent's Embrace territory",
                "sanitation infrastructure security",
            ],
            "reason": "Waste Management Sector is within the Undergrid and requires proper access through tunnel networks, with Slicktails and Serpent's Embrace shared control",
        },
    },
    {
        "location_name": "Driftmark",
        "location_type": "CITY",
        "facts": [
            "Driftmark is a separate city from Neotopia",
            "Driftmark is a port city accessible by land or sea",
            "Cannot be reached by jumping through tunnels",
            "Requires proper travel from Neotopia or Agrihaven",
            "Driftmark is not directly connected to the Undergrid",
            "Driftmark features port facilities and maritime infrastructure",
            "The city is known for trade and maritime commerce",
            "Driftmark has a mix of port workers and traders",
            "The area operates on natural day/night cycles",
            "Travel to Driftmark takes several hours by vehicle or maritime transport",
            "Driftmark is a hub for inter-city trade and commerce",
        ],
        "connections": {
            "requires_travel": ["Neotopia", "Agrihaven"],
            "not_connected": ["The Undergrid"],
        },
        "travel_requirements": {
            "Neotopia": {
                "method": "vehicle, transport lane, or maritime transport",
                "time": "several hours",
                "distance": "approximately 250 kilometers",
                "terrain": "coastal routes, port access, varied terrain",
                "requirements": ["transportation", "proper route"],
                "hazards": ["coastal weather", "port security", "maritime traffic"],
                "cost": "moderate transport fees",
                "description": "Driftmark is a port city accessible by land or sea transport. The journey takes several hours across varied terrain.",
            },
            "Agrihaven": {
                "method": "vehicle or transport",
                "time": "several hours",
                "distance": "approximately 150 kilometers",
                "terrain": "agricultural zones, coastal routes",
                "requirements": ["transportation", "proper route"],
                "hazards": ["weather conditions", "rural checkpoints"],
                "cost": "moderate transport fees",
                "description": "Travel to Driftmark from Agrihaven takes several hours through agricultural and coastal terrain.",
            },
        },
        "physical_properties": {
            "elevation": "sea level, coastal terrain",
            "accessibility": "port access, ground transport, maritime transport",
            "size": "moderate port city with maritime infrastructure",
            "architecture": "port facilities, maritime buildings, trade centers, coastal architecture",
            "climate": "coastal weather patterns, maritime climate, natural variations",
            "lighting": "natural daylight, port lighting, moderate artificial lighting",
            "population_density": "moderate, port workers and traders",
            "security_level": "moderate, port security, trade regulations",
            "atmosphere": "port activity, maritime sounds, trade hustle, coastal wind, seagulls",
        },
        "constraints": {
            "cannot_reach_by": ["jump", "tunnel jump", "instant travel", "walking from Undergrid"],
            "requires": [
                "transportation for inter-city travel",
                "port access for maritime transport",
            ],
            "forbidden_actions": [
                "unauthorized port access",
                "smuggling violations",
                "trade regulation violations",
            ],
            "restrictions": [
                "port security zones",
                "trade regulations",
                "maritime traffic control",
            ],
            "reason": "Driftmark is a separate port city that cannot be reached by jumping through tunnels or instant travel",
        },
    },
    {
        "location_name": "Skyward Nexus",
        "location_type": "CITY",
        "facts": [
            "Skyward Nexus is a separate elite aerial city",
            "Skyward Nexus is accessible only by specialized aerial transport",
            "Cannot be reached by jumping through tunnels or ground travel",
            "Requires proper travel from Neotopia with elite authorization",
            "Skyward Nexus is not directly connected to the Undergrid or other cities",
            "Skyward Nexus features elite aerial architecture and sky-bridges",
            "The city is known for elite residents and exclusive access",
            "Skyward Nexus has high security and restricted access",
            "The area operates on artificial day/night cycles",
            "Travel to Skyward Nexus requires specialized aerial transport and elite authorization",
            "Skyward Nexus is a symbol of ultimate luxury and exclusivity",
        ],
        "connections": {
            "requires_travel": ["Neotopia"],
            "not_connected": ["The Undergrid", "Agrihaven", "Driftmark"],
        },
        "travel_requirements": {
            "Neotopia": {
                "method": "aerial transport or sky-bridge",
                "time": "several hours",
                "distance": "aerial distance varies",
                "terrain": "aerial routes, sky-bridges",
                "requirements": ["aerial transportation", "proper route", "elite authorization"],
                "hazards": ["aerial traffic control", "weather conditions", "security clearance"],
                "cost": "very expensive, elite-only access",
                "description": "Skyward Nexus is an elite aerial city. Access requires specialized aerial transport and often elite authorization.",
            },
        },
        "physical_properties": {
            "elevation": "aerial, elevated above ground level",
            "accessibility": "aerial transport only, sky-bridges, elite access points",
            "size": "moderate elite aerial city",
            "architecture": "aerial architecture, sky-bridges, elite structures, floating platforms",
            "climate": "climate-controlled, artificial weather, perfect conditions",
            "lighting": "bright elite lighting, holographic displays, 24/7 illumination",
            "population_density": "low, elite residents only",
            "security_level": "very high, elite security, restricted access",
            "atmosphere": "elite activity, aerial sounds, exclusive ambiance, luxury environment",
        },
        "constraints": {
            "cannot_reach_by": [
                "jump",
                "tunnel jump",
                "instant travel",
                "ground transport",
                "walking",
            ],
            "requires": [
                "aerial transportation",
                "elite authorization",
                "proper security clearance",
            ],
            "forbidden_actions": [
                "unauthorized aerial access",
                "bypassing security",
                "elite area violations",
            ],
            "restrictions": [
                "elite authorization required",
                "aerial traffic control",
                "restricted airspace",
                "exclusive access only",
            ],
            "reason": "Skyward Nexus is an elite aerial city that requires specialized aerial transport and elite authorization",
        },
    },
]


async def seed_world_regions(postgres_manager: "PostgresManager") -> dict[UUID, WorldRegion]:
    """
    Seed world regions into the database.

    Args:
        postgres_manager: PostgreSQL manager instance

    Returns:
        Dictionary mapping region IDs to WorldRegion instances
    """
    from ds_common.repository.world_region import WorldRegionRepository

    logger.info("Seeding world regions...")
    repo = WorldRegionRepository(postgres_manager)
    seeded_regions: dict[UUID, WorldRegion] = {}

    for region_data in WORLD_REGIONS:
        region_id = region_data["id"]
        existing = await repo.get_by_id(region_id)
        if existing:
            logger.debug(f"World region '{region_data['name']}' already exists, skipping")
            seeded_regions[region_id] = existing
            continue

        world_region = WorldRegion(
            id=region_id,
            name=region_data["name"],
            region_type=region_data["region_type"],
            description=region_data.get("description"),
            city=region_data.get("city"),
            parent_region_id=region_data.get("parent_region_id"),
            hierarchy_level=region_data.get("hierarchy_level", 0),
            locations=region_data.get("locations", []),
            factions=region_data.get("factions", []),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        created = await repo.create(world_region)
        seeded_regions[region_id] = created
        logger.info(f"Created world region: {region_data['name']}")

    return seeded_regions


async def seed_calendar_events(postgres_manager: "PostgresManager") -> dict[UUID, CalendarEvent]:
    """
    Seed calendar events into the database.

    Args:
        postgres_manager: PostgreSQL manager instance

    Returns:
        Dictionary mapping calendar event IDs to CalendarEvent instances
    """
    from ds_common.repository.calendar_event import CalendarEventRepository

    logger.info("Seeding calendar events...")
    repo = CalendarEventRepository(postgres_manager)
    seeded_events: dict[UUID, CalendarEvent] = {}

    for event_data in CALENDAR_EVENTS:
        event_id = event_data["id"]
        existing = await repo.get_by_id(event_id)
        if existing:
            logger.debug(f"Calendar event '{event_data['name']}' already exists, skipping")
            seeded_events[event_id] = existing
            continue

        calendar_event = CalendarEvent(
            id=event_id,
            name=event_data["name"],
            event_type=event_data["event_type"],
            description=event_data.get("description"),
            start_game_time=event_data["start_game_time"],
            end_game_time=event_data["end_game_time"],
            is_recurring=event_data.get("is_recurring", True),
            recurrence=event_data.get("recurrence"),
            regional_variations=event_data.get("regional_variations"),
            faction_specific=event_data.get("faction_specific", False),
            affected_factions=event_data.get("affected_factions", []),
            seasonal=event_data.get("seasonal", False),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        created = await repo.create(calendar_event)
        seeded_events[event_id] = created
        logger.info(f"Created calendar event: {event_data['name']}")

    return seeded_events


async def seed_location_facts(
    postgres_manager: "PostgresManager", world_regions: dict[UUID, WorldRegion]
) -> dict[str, LocationFact]:
    """
    Seed location facts into the database.

    Args:
        postgres_manager: PostgreSQL manager instance
        world_regions: Dictionary of seeded world regions (for region_id mapping)

    Returns:
        Dictionary mapping location names to LocationFact instances
    """
    from ds_common.repository.location_fact import LocationFactRepository

    logger.info("Seeding location facts...")
    repo = LocationFactRepository(postgres_manager)
    seeded_facts: dict[str, LocationFact] = {}

    for fact_data in LOCATION_FACTS:
        location_name = fact_data["location_name"]
        existing = await repo.get_by_location_name(location_name, case_sensitive=False)
        if existing:
            logger.debug(f"Location fact '{location_name}' already exists, skipping")
            seeded_facts[location_name] = existing
            continue

        # Try to find matching region
        region_id = None
        for region in world_regions.values():
            if region.name == location_name or location_name in region.locations:
                region_id = region.id
                break

        location_fact = LocationFact(
            location_name=fact_data["location_name"],
            location_type=fact_data["location_type"],
            facts=fact_data.get("facts", []),
            connections=fact_data.get("connections", {}),
            travel_requirements=fact_data.get("travel_requirements", {}),
            physical_properties=fact_data.get("physical_properties", {}),
            region_id=region_id,
            constraints=fact_data.get("constraints", {}),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        created = await repo.create(location_fact)
        seeded_facts[location_name] = created
        logger.info(f"Created location fact: {location_name}")

    logger.info(f"Seeded {len(seeded_facts)} location facts.")
    return seeded_facts


async def seed_baseline_world_memories(
    postgres_manager: "PostgresManager",
) -> dict[UUID, WorldMemory]:
    """
    Seed baseline world memories into the database.

    Args:
        postgres_manager: PostgreSQL manager instance

    Returns:
        Dictionary mapping memory IDs to WorldMemory instances
    """
    from ds_common.repository.world_memory import WorldMemoryRepository

    logger.info("Seeding baseline world memories...")
    repo = WorldMemoryRepository(postgres_manager)
    seeded_memories: dict[UUID, WorldMemory] = {}

    for memory_data in BASELINE_WORLD_MEMORIES:
        memory_id = memory_data["id"]
        existing = await repo.get_by_id(memory_id)
        if existing:
            logger.debug(f"World memory '{memory_data['title']}' already exists, skipping")
            seeded_memories[memory_id] = existing
            continue

        world_memory = WorldMemory(
            id=memory_id,
            memory_category=memory_data["memory_category"],
            title=memory_data["title"],
            description=memory_data["description"],
            full_narrative=memory_data.get("full_narrative"),
            impact_level=memory_data.get("impact_level"),
            is_public=memory_data.get("is_public", True),
            tags=memory_data.get("tags", []),
            related_entities=memory_data.get("related_entities"),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        created = await repo.create(world_memory)
        seeded_memories[memory_id] = created
        logger.info(f"Created world memory: {memory_data['title']}")

    return seeded_memories


async def seed_world_items(postgres_manager: "PostgresManager") -> dict[UUID, WorldItem]:
    """
    Seed world items into the database (placeholder for future items).

    Args:
        postgres_manager: PostgreSQL manager instance

    Returns:
        Dictionary mapping item IDs to WorldItem instances
    """
    from ds_common.repository.world_item import WorldItemRepository

    logger.info("Seeding world items...")
    repo = WorldItemRepository(postgres_manager)
    seeded_items: dict[UUID, WorldItem] = {}

    # No items to seed yet, but structure is ready
    logger.info("No world items to seed at this time")

    return seeded_items


async def seed_calendar_months(postgres_manager: "PostgresManager") -> dict[int, "CalendarMonth"]:
    """
    Seed calendar months into the database.

    Args:
        postgres_manager: PostgreSQL manager instance

    Returns:
        Dictionary mapping month numbers to CalendarMonth instances
    """
    from ds_common.models.calendar_month import CalendarMonth
    from ds_common.repository.calendar_month import CalendarMonthRepository

    logger.info("Seeding calendar months...")
    repo = CalendarMonthRepository(postgres_manager)
    seeded_months: dict[int, CalendarMonth] = {}

    # 20 months: 4 peak months (27 days) centered on season peaks + 16 regular months (18-19 days)
    # Peak months: Month 3 (Spring, day 50), Month 8 (Summer, day 150),
    #              Month 13 (Fall, day 250), Month 18 (Winter, day 350)
    # Structure: [18, 18, 27, 19, 18] per season × 4 seasons = 400 days
    # Day ranges: Spring (1-100), Summer (101-200), Fall (201-300), Winter (301-400)
    CALENDAR_MONTHS = [
        # SPRING (days 1-100)
        {
            "month_number": 1,
            "name": "Thaw",
            "short_name": "Thaw",
            "days": 18,
            "season": "SPRING",
            "description": "The month when winter's grip finally loosens and the first signs of spring emerge.",
            "history": "Named for the thawing of frozen ground and waterways. In ancient times, this marked the beginning of the planting season and was celebrated with festivals of renewal.",
            "cultural_significance": {
                "factions": ["Agrihaven Farmers", "Neotopia Corporate"],
                "traditions": ["First Planting Ceremony", "Thaw Festival"],
                "events": ["Agricultural planning begins", "Corporate fiscal year start"],
            },
        },
        {
            "month_number": 2,
            "name": "Bloom",
            "short_name": "Bloom",
            "days": 18,
            "season": "SPRING",
            "description": "When flowers and crops begin to bloom across the land.",
            "history": "The month of blooming was once considered sacred by agricultural communities. The name dates back to pre-Corporate times when farming was the primary occupation.",
            "cultural_significance": {
                "factions": ["Agrihaven Farmers"],
                "traditions": ["Bloom Festival", "Harvest Blessing"],
                "events": ["First harvest celebrations"],
            },
        },
        {
            "month_number": 3,
            "name": "Verdant Peak",
            "short_name": "VerdPeak",
            "days": 27,
            "season": "SPRING",
            "description": "The peak of spring, when nature reaches its fullest green and most vibrant state. This is the longest month of spring, centered on the season's midpoint.",
            "history": "The 'Peak' months were established in ancient times to honor the height of each season. Verdant Peak represents the absolute zenith of spring's growth and vitality.",
            "cultural_significance": {
                "factions": ["Agrihaven Farmers", "All"],
                "traditions": [
                    "Verdant Peak Festival",
                    "Peak of Growth Celebrations",
                    "Green Abundance Rituals",
                ],
                "events": [
                    "Peak harvest season",
                    "Major agricultural markets",
                    "City-wide spring festivals",
                ],
            },
        },
        {
            "month_number": 4,
            "name": "Radiance",
            "short_name": "Radi",
            "days": 19,
            "season": "SPRING",
            "description": "The brightest month of spring, when the sun's warmth fully returns and shadows shrink.",
            "history": "Named for the radiant quality of sunlight during this period. Ancient texts describe it as 'the month when shadows shrink and light prevails'.",
            "cultural_significance": {
                "factions": ["All"],
                "traditions": ["Day of Radiance", "Solar Celebrations"],
                "events": ["City-wide festivals"],
            },
        },
        {
            "month_number": 5,
            "name": "Growth",
            "short_name": "Grow",
            "days": 18,
            "season": "SPRING",
            "description": "The month of rapid growth and expansion, both in nature and commerce, as spring transitions toward summer.",
            "history": "Originally called 'Rapid Growth' by early settlers, it was shortened over time. Corporate interests later adopted the name to represent economic expansion.",
            "cultural_significance": {
                "factions": ["Neotopia Corporate", "Agrihaven Farmers"],
                "traditions": ["Growth Summit", "Trade Fair"],
                "events": ["Major trade negotiations"],
            },
        },
        # SUMMER (days 101-200)
        {
            "month_number": 6,
            "name": "Solstice",
            "short_name": "Sol",
            "days": 18,
            "season": "SUMMER",
            "description": "The month containing the summer solstice, the longest day of the year.",
            "history": "One of the oldest month names, dating back to pre-Corporate astronomical observations. The solstice was a major religious and cultural event.",
            "cultural_significance": {
                "factions": ["All"],
                "traditions": ["Solstice Festival", "Day of Long Light"],
                "events": ["Major celebrations across all regions"],
            },
        },
        {
            "month_number": 7,
            "name": "Heat",
            "short_name": "Heat",
            "days": 18,
            "season": "SUMMER",
            "description": "The month when temperatures begin to peak, building toward summer's zenith.",
            "history": "Simply named for the intense heat. In the Undergrid, this month is particularly challenging due to poor ventilation.",
            "cultural_significance": {
                "factions": ["Undergrid Workers"],
                "traditions": ["Heat Relief Programs", "Cooling Stations"],
                "events": ["Worker strikes often occur"],
            },
        },
        {
            "month_number": 8,
            "name": "Inferno Peak",
            "short_name": "Inferno",
            "days": 27,
            "season": "SUMMER",
            "description": "The absolute peak of summer, when heat and light reach their maximum intensity. This is the longest month of summer, centered on the season's midpoint.",
            "history": "The 'Peak' months honor the height of each season. Inferno Peak represents the zenith of summer's fire and intensity, when the world burns brightest.",
            "cultural_significance": {
                "factions": ["Neotopia Corporate", "All"],
                "traditions": [
                    "Inferno Peak Festival",
                    "Peak of Fire Celebrations",
                    "Ambition Day",
                    "Corporate Achievement Awards",
                ],
                "events": ["Quarterly reviews", "Major corporate events", "Peak heat celebrations"],
            },
        },
        {
            "month_number": 9,
            "name": "Ember",
            "short_name": "Emb",
            "days": 19,
            "season": "SUMMER",
            "description": "The fading embers of summer, when heat begins to wane but still burns strong.",
            "history": "Named for the dying embers of summer fires. This month marks the transition from peak summer to the cooling period.",
            "cultural_significance": {
                "factions": ["All"],
                "traditions": ["Ember Festival", "Transition Rituals"],
                "events": ["Preparation for harvest"],
            },
        },
        {
            "month_number": 10,
            "name": "Flame",
            "short_name": "Flam",
            "days": 18,
            "season": "SUMMER",
            "description": "Named for the fiery intensity that still lingers as summer draws to a close.",
            "history": "The name 'Flame' comes from ancient fire festivals that marked the height of summer. Corporate era repurposed it to represent 'burning ambition'.",
            "cultural_significance": {
                "factions": ["Neotopia Corporate"],
                "traditions": ["Ambition Day", "Corporate Achievement Awards"],
                "events": ["Quarterly reviews"],
            },
        },
        # FALL (days 201-300)
        {
            "month_number": 11,
            "name": "Harvest",
            "short_name": "Harv",
            "days": 18,
            "season": "FALL",
            "description": "The primary harvest month when crops are gathered and stored for winter.",
            "history": "The most important month for agricultural communities. The name is ancient and universal across all cultures.",
            "cultural_significance": {
                "factions": ["Agrihaven Farmers"],
                "traditions": ["Harvest Festival", "Thanksgiving"],
                "events": ["Major agricultural markets"],
            },
        },
        {
            "month_number": 12,
            "name": "Crimson",
            "short_name": "Crim",
            "days": 18,
            "season": "FALL",
            "description": "The month when leaves turn crimson and red, painting the world in autumn's colors.",
            "history": "Named for the crimson color of autumn foliage. In some regions, this month is associated with blood and sacrifice in ancient traditions.",
            "cultural_significance": {
                "factions": ["Undergrid Workers", "Faction territories"],
                "traditions": ["Crimson Festival", "Remembrance Day"],
                "events": ["Historical commemorations"],
            },
        },
        {
            "month_number": 13,
            "name": "Fulcrum Peak",
            "short_name": "Fulcrum",
            "days": 27,
            "season": "FALL",
            "description": "The peak of autumn, the turning point between warmth and cold. This is the longest month of fall, centered on the season's midpoint, when the world balances between light and darkness.",
            "history": "The 'Peak' months honor the height of each season. Fulcrum Peak represents the perfect balance point of autumn, when the year pivots toward winter.",
            "cultural_significance": {
                "factions": ["All"],
                "traditions": [
                    "Fulcrum Peak Festival",
                    "Balance Day",
                    "Equilibrium Rituals",
                    "Dusk Vigil",
                ],
                "events": ["Major cultural events", "Preparation for winter", "Year-end planning"],
            },
        },
        {
            "month_number": 14,
            "name": "Dusk",
            "short_name": "Dusk",
            "days": 19,
            "season": "FALL",
            "description": "The month of lengthening shadows and early darkness, as fall deepens.",
            "history": "Named for the earlier sunsets and longer nights. Symbolically represents the 'dusk' of the year before winter.",
            "cultural_significance": {
                "factions": ["All"],
                "traditions": ["Dusk Vigil", "Shadow Festivals"],
                "events": ["Preparation for winter"],
            },
        },
        {
            "month_number": 15,
            "name": "Frost",
            "short_name": "Frost",
            "days": 18,
            "season": "FALL",
            "description": "The first month when frost appears, marking the transition to winter.",
            "history": "The month when the first frosts arrive. Historically marked the end of the growing season and beginning of winter preparations.",
            "cultural_significance": {
                "factions": ["Agrihaven Farmers"],
                "traditions": ["First Frost Ceremony", "Winter Preparation"],
                "events": ["End of harvest season"],
            },
        },
        # WINTER (days 301-400)
        {
            "month_number": 16,
            "name": "Ice",
            "short_name": "Ice",
            "days": 18,
            "season": "WINTER",
            "description": "The month when ice begins to cover everything, marking winter's arrival.",
            "history": "Named simply for the ice that dominates this period. In the Undergrid, this month brings relief from heat but new challenges with frozen pipes.",
            "cultural_significance": {
                "factions": ["Undergrid Workers"],
                "traditions": ["Ice Festival", "Survival Celebrations"],
                "events": ["Infrastructure maintenance"],
            },
        },
        {
            "month_number": 17,
            "name": "Deep",
            "short_name": "Deep",
            "days": 18,
            "season": "WINTER",
            "description": "The deep winter month, when cold and darkness deepen as winter approaches its peak.",
            "history": "Named for the 'deep' cold and darkness of mid-winter. This was traditionally the hardest month for survival.",
            "cultural_significance": {
                "factions": ["All"],
                "traditions": ["Deep Winter Festival", "Survival Stories"],
                "events": ["Community support programs"],
            },
        },
        {
            "month_number": 18,
            "name": "Gloom Peak",
            "short_name": "GloomPeak",
            "days": 27,
            "season": "WINTER",
            "description": "The absolute peak of winter, the darkest and coldest point of the year. This is the longest month of winter, centered on the season's midpoint, when darkness and cold reach their zenith.",
            "history": "The 'Peak' months honor the height of each season. Gloom Peak represents the absolute depth of winter's darkness and cold, the hardest time of the year.",
            "cultural_significance": {
                "factions": ["All", "Undergrid Workers"],
                "traditions": [
                    "Gloom Peak Festival",
                    "Peak of Darkness Vigil",
                    "Light Festivals",
                    "Survival Celebrations",
                ],
                "events": [
                    "Mental health awareness",
                    "Community support programs",
                    "Year's darkest celebrations",
                ],
            },
        },
        {
            "month_number": 19,
            "name": "Stir",
            "short_name": "Stir",
            "days": 19,
            "season": "WINTER",
            "description": "The month when life begins to stir again beneath the frozen surface, preparing for spring.",
            "history": "Named for the 'stirring' of life beneath the frozen surface. This month represents hope and the promise of renewal.",
            "cultural_significance": {
                "factions": ["All"],
                "traditions": ["Stir Festival", "Renewal Ceremonies"],
                "events": ["Planning for spring"],
            },
        },
        {
            "month_number": 20,
            "name": "Awakening",
            "short_name": "Awak",
            "days": 18,
            "season": "WINTER",
            "description": "The final month of winter when nature begins to awaken, bridging winter and spring.",
            "history": "The month of awakening, when the first signs of spring appear. This month bridges winter and spring, full of anticipation.",
            "cultural_significance": {
                "factions": ["All"],
                "traditions": ["Awakening Festival", "New Year Preparations"],
                "events": ["Year-end celebrations"],
            },
        },
    ]

    for month_data in CALENDAR_MONTHS:
        existing = await repo.get_by_month_number(month_data["month_number"])
        if existing:
            logger.debug(
                f"Month {month_data['month_number']} ({month_data['name']}) already exists, skipping"
            )
            seeded_months[month_data["month_number"]] = existing
            continue

        month = CalendarMonth(**month_data)
        month = await repo.create(month)
        seeded_months[month_data["month_number"]] = month
        logger.debug(f"Seeded month {month.month_number}: {month.name}")

    logger.info(f"Seeded {len(seeded_months)} calendar months")
    return seeded_months


async def seed_calendar_year_cycle(
    postgres_manager: "PostgresManager",
) -> dict[int, "CalendarYearCycle"]:
    """
    Seed calendar year cycle (12-year cycle with randomized animals) into the database.

    Args:
        postgres_manager: PostgreSQL manager instance

    Returns:
        Dictionary mapping cycle year numbers to CalendarYearCycle instances
    """
    from ds_common.models.calendar_year_cycle import CalendarYearCycle
    from ds_common.repository.calendar_year_cycle import CalendarYearCycleRepository

    logger.info("Seeding calendar year cycle...")
    repo = CalendarYearCycleRepository(postgres_manager)
    seeded_cycles: dict[int, CalendarYearCycle] = {}

    # Randomized animals (not traditional Chinese zodiac)
    import random

    # Pool of potential animals for the cycle
    animal_pool = [
        "Shadow",
        "Iron",
        "Crystal",
        "Neon",
        "Steel",
        "Chrome",
        "Void",
        "Quantum",
        "Nano",
        "Cyber",
        "Data",
        "Code",
    ]

    # Shuffle to randomize
    random.shuffle(animal_pool)

    # 12-year cycle with randomized animals
    CYCLE_YEARS = [
        {
            "cycle_year": 1,
            "animal_name": animal_pool[0],
            "animal_description": f"The {animal_pool[0]} year represents innovation and new beginnings.",
            "traits": ["Innovative", "Bold", "Forward-thinking"],
            "cultural_significance": f"Years of the {animal_pool[0]} are associated with technological breakthroughs and corporate expansion.",
        },
        {
            "cycle_year": 2,
            "animal_name": animal_pool[1],
            "animal_description": f"The {animal_pool[1]} year represents stability and foundation.",
            "traits": ["Stable", "Reliable", "Grounded"],
            "cultural_significance": f"Years of the {animal_pool[1]} mark periods of infrastructure development and consolidation.",
        },
        {
            "cycle_year": 3,
            "animal_name": animal_pool[2],
            "animal_description": f"The {animal_pool[2]} year represents growth and expansion.",
            "traits": ["Expansive", "Ambitious", "Dynamic"],
            "cultural_significance": f"Years of the {animal_pool[2]} are known for economic growth and territorial expansion.",
        },
        {
            "cycle_year": 4,
            "animal_name": animal_pool[3],
            "animal_description": f"The {animal_pool[3]} year represents illumination and clarity.",
            "traits": ["Illuminating", "Clear", "Revealing"],
            "cultural_significance": f"Years of the {animal_pool[3]} bring revelations and discoveries.",
        },
        {
            "cycle_year": 5,
            "animal_name": animal_pool[4],
            "animal_description": f"The {animal_pool[4]} year represents strength and resilience.",
            "traits": ["Strong", "Resilient", "Enduring"],
            "cultural_significance": f"Years of the {animal_pool[4]} test the mettle of factions and individuals.",
        },
        {
            "cycle_year": 6,
            "animal_name": animal_pool[5],
            "animal_description": f"The {animal_pool[5]} year represents transformation and change.",
            "traits": ["Transformative", "Adaptive", "Evolving"],
            "cultural_significance": f"Years of the {animal_pool[5]} mark significant shifts in power and society.",
        },
        {
            "cycle_year": 7,
            "animal_name": animal_pool[6],
            "animal_description": f"The {animal_pool[6]} year represents mystery and the unknown.",
            "traits": ["Mysterious", "Unknown", "Hidden"],
            "cultural_significance": f"Years of the {animal_pool[6]} are associated with secrets and hidden knowledge.",
        },
        {
            "cycle_year": 8,
            "animal_name": animal_pool[7],
            "animal_description": f"The {animal_pool[7]} year represents precision and calculation.",
            "traits": ["Precise", "Calculated", "Analytical"],
            "cultural_significance": f"Years of the {animal_pool[7]} favor strategic planning and careful execution.",
        },
        {
            "cycle_year": 9,
            "animal_name": animal_pool[8],
            "animal_description": f"The {animal_pool[8]} year represents connection and networks.",
            "traits": ["Connected", "Networked", "Interlinked"],
            "cultural_significance": f"Years of the {animal_pool[8]} strengthen alliances and communication networks.",
        },
        {
            "cycle_year": 10,
            "animal_name": animal_pool[9],
            "animal_description": f"The {animal_pool[9]} year represents digital dominance and virtual realms.",
            "traits": ["Digital", "Virtual", "Networked"],
            "cultural_significance": f"Years of the {animal_pool[9]} see advances in digital infrastructure and virtual spaces.",
        },
        {
            "cycle_year": 11,
            "animal_name": animal_pool[10],
            "animal_description": f"The {animal_pool[10]} year represents information and knowledge.",
            "traits": ["Informative", "Knowledgeable", "Data-driven"],
            "cultural_significance": f"Years of the {animal_pool[10]} are marked by information wars and data conflicts.",
        },
        {
            "cycle_year": 12,
            "animal_name": animal_pool[11],
            "animal_description": f"The {animal_pool[11]} year represents completion and new cycles.",
            "traits": ["Completing", "Cyclical", "Renewing"],
            "cultural_significance": f"Years of the {animal_pool[11]} complete the cycle and prepare for renewal.",
        },
    ]

    for cycle_data in CYCLE_YEARS:
        existing = await repo.get_by_cycle_year(cycle_data["cycle_year"])
        if existing:
            logger.debug(
                f"Cycle year {cycle_data['cycle_year']} ({cycle_data['animal_name']}) already exists, skipping"
            )
            seeded_cycles[cycle_data["cycle_year"]] = existing
            continue

        cycle = CalendarYearCycle(**cycle_data)
        cycle = await repo.create(cycle)
        seeded_cycles[cycle_data["cycle_year"]] = cycle
        logger.debug(f"Seeded cycle year {cycle.cycle_year}: {cycle.animal_name}")

    logger.info(f"Seeded {len(seeded_cycles)} calendar year cycles")
    return seeded_cycles


async def seed_all_world_data(postgres_manager: "PostgresManager") -> None:
    """
    Seed all world data into the database.

    Args:
        postgres_manager: PostgreSQL manager instance
    """
    logger.info("Starting world data seeding...")

    world_regions = await seed_world_regions(postgres_manager)
    await seed_calendar_year_cycle(postgres_manager)
    await seed_calendar_months(postgres_manager)
    await seed_calendar_events(postgres_manager)
    await seed_baseline_world_memories(postgres_manager)
    await seed_world_items(postgres_manager)
    await seed_location_facts(postgres_manager, world_regions)

    logger.info("World data seeding completed!")


if __name__ == "__main__":
    import asyncio
    import os

    from dotenv import load_dotenv

    from ds_discord_bot.postgres_manager import PostgresManager

    # Load environment variables
    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    async def main():
        postgres_manager = await PostgresManager.create(
            host=os.getenv("DS_POSTGRES_HOST", "localhost"),
            port=int(os.getenv("DS_POSTGRES_PORT", "5432")),
            database=os.getenv("DS_POSTGRES_DATABASE", "game"),
            user=os.getenv("DS_POSTGRES_USER", "postgres"),
            password=os.getenv("DS_POSTGRES_PASSWORD", "postgres"),
            pool_size=int(os.getenv("DS_POSTGRES_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("DS_POSTGRES_MAX_OVERFLOW", "10")),
            echo=os.getenv("DS_POSTGRES_ECHO", "false").lower() == "true",
        )

        try:
            await seed_all_world_data(postgres_manager)
        finally:
            await postgres_manager.close()

    asyncio.run(main())
