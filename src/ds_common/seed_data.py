"""
Seed data for initializing the database with default game data.

This module contains seed data ported from the SurrealDB schema definitions.
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

# Import all models to ensure SQLAlchemy can resolve relationships
from ds_common.models.character import Character  # noqa: F401
from ds_common.models.character_class import CharacterClass
from ds_common.models.character_stat import CharacterStat
from ds_common.models.game_session import GameSession  # noqa: F401
from ds_common.models.item_category import ItemCategory
from ds_common.models.item_template import ItemTemplate
from ds_common.models.player import Player  # noqa: F401
from ds_common.models.quest import Quest  # noqa: F401

if TYPE_CHECKING:
    from ds_discord_bot.postgres_manager import PostgresManager

logger = logging.getLogger(__name__)

# Character Classes seed data (from db/game.surql)
CHARACTER_CLASSES = [
    {
        "id": UUID("00000000-0000-0000-0000-000000000001"),
        "name": "Enforcer",
        "description": "A physically imposing character who handles the physical aspects of maintaining order within the organization. This character could be designed with a robust, tank-like build and might feature visible cybernetic enhancements that augment their strength and durability.",
        "emoji": "🛡️",
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000002"),
        "name": "Tech Wizard",
        "description": "A master of technology and hacking, this character supports the organization by manipulating cyber systems, gathering information, and controlling communication. They could have a more wiry build with tools and tech gadgets integrated into their attire.",
        "emoji": "💻",
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000003"),
        "name": "Smooth Talker",
        "description": "This character is the face of the organization for negotiations and dealings with other factions. Charismatic and clever, they can manipulate situations to their favor. Their design might include stylish, sleek clothing that reflects their charisma and social prowess.",
        "emoji": "💬",
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000004"),
        "name": "Spy",
        "description": "Stealthy and elusive, this character specializes in gathering intelligence and carrying out covert operations. They could be depicted with a mysterious, cloaked appearance, equipped with gadgets for espionage.",
        "emoji": "🕵️",
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000005"),
        "name": "Wild Card",
        "description": "Unpredictable and volatile, this character adds an element of surprise and unpredictability. Their appearance could be eccentric, with mismatched cybernetics and colorful attire, reflecting their unpredictable nature.",
        "emoji": "🃏",
    },
]

# Character Stats seed data (from db/game.surql)
CHARACTER_STATS = [
    {
        "id": UUID("00000000-0000-0000-0000-000000000101"),
        "name": "Strength",
        "abbr": "STR",
        "description": "This measures the physical power of a character. It is essential for characters like the Enforcer, who rely on melee strength to overpower foes.",
        "emoji": "💪",
        "max_value": 100,
        "is_primary": True,
        "is_mutable": True,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000102"),
        "name": "Dexterity",
        "abbr": "DEX",
        "description": "This stat reflects agility, reflexes, and balance. It is crucial for classes such as the Spy, who must perform stealthy movements, and also impacts the effectiveness of ranged attacks, making it important for the Wild Card as well.",
        "emoji": "🤸‍♀️",
        "max_value": 100,
        "is_primary": True,
        "is_mutable": True,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000103"),
        "name": "Intellect",
        "abbr": "INT",
        "description": "Intellect governs reasoning, memory, and the ability to understand complex systems, making it a key stat for the Tech Wizard. This stat would also influence abilities related to technology manipulation, hacking, and understanding complex machinery or systems.",
        "emoji": "🧠",
        "max_value": 100,
        "is_primary": True,
        "is_mutable": True,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000104"),
        "name": "Charisma",
        "abbr": "CHA",
        "description": "Charisma represents a character's social skills, including the ability to persuade, lead, and influence others. It is particularly vital for the Smooth Talker, who navigates political landscapes and manipulates others to achieve their goals.",
        "emoji": "🤝",
        "max_value": 100,
        "is_primary": True,
        "is_mutable": True,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000105"),
        "name": "Perception",
        "abbr": "PER",
        "description": "This stat encompasses awareness, intuition, and insight, helping characters to notice hidden details, read social cues, and often get a sense of their surroundings faster than others. It's crucial for the Spy for gathering intelligence and for the Wild Card whose adaptability can benefit from good situational awareness.",
        "emoji": "👁️",
        "max_value": 100,
        "is_primary": True,
        "is_mutable": True,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000106"),
        "name": "Luck",
        "abbr": "LUK",
        "description": "Luck represents a character's ability to get lucky or avoid bad luck. It can impact various aspects of their experience, such as avoiding traps, landing on good deals, or getting unexpected assistance.",
        "emoji": "🍀",
        "max_value": 100,
        "is_primary": True,
        "is_mutable": False,
    },
]

# Character Class to Stat relationships
# Format: (character_class_id, character_stat_id)
CLASS_STAT_RELATIONSHIPS = [
    # Enforcer: STR, DEX
    (
        UUID("00000000-0000-0000-0000-000000000001"),
        UUID("00000000-0000-0000-0000-000000000101"),
    ),  # STR
    (
        UUID("00000000-0000-0000-0000-000000000001"),
        UUID("00000000-0000-0000-0000-000000000102"),
    ),  # DEX
    # Tech Wizard: INT, DEX
    (
        UUID("00000000-0000-0000-0000-000000000002"),
        UUID("00000000-0000-0000-0000-000000000103"),
    ),  # INT
    (
        UUID("00000000-0000-0000-0000-000000000002"),
        UUID("00000000-0000-0000-0000-000000000102"),
    ),  # DEX
    # Smooth Talker: CHA, INT
    (
        UUID("00000000-0000-0000-0000-000000000003"),
        UUID("00000000-0000-0000-0000-000000000104"),
    ),  # CHA
    (
        UUID("00000000-0000-0000-0000-000000000003"),
        UUID("00000000-0000-0000-0000-000000000103"),
    ),  # INT
    # Spy: DEX, PER
    (
        UUID("00000000-0000-0000-0000-000000000004"),
        UUID("00000000-0000-0000-0000-000000000102"),
    ),  # DEX
    (
        UUID("00000000-0000-0000-0000-000000000004"),
        UUID("00000000-0000-0000-0000-000000000105"),
    ),  # PER
    # Wild Card: STR, DEX, INT, CHA, PER
    (
        UUID("00000000-0000-0000-0000-000000000005"),
        UUID("00000000-0000-0000-0000-000000000101"),
    ),  # STR
    (
        UUID("00000000-0000-0000-0000-000000000005"),
        UUID("00000000-0000-0000-0000-000000000102"),
    ),  # DEX
    (
        UUID("00000000-0000-0000-0000-000000000005"),
        UUID("00000000-0000-0000-0000-000000000103"),
    ),  # INT
    (
        UUID("00000000-0000-0000-0000-000000000005"),
        UUID("00000000-0000-0000-0000-000000000104"),
    ),  # CHA
    (
        UUID("00000000-0000-0000-0000-000000000005"),
        UUID("00000000-0000-0000-0000-000000000105"),
    ),  # PER
]

# Item Categories seed data
ITEM_CATEGORIES = [
    {
        "id": UUID("00000000-0000-0000-0000-000000001001"),
        "name": "weapon",
        "description": "Weapons for combat - melee, ranged, and tech weapons",
        "emoji": "⚔️",
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000001002"),
        "name": "armor",
        "description": "Protective armor pieces",
        "emoji": "🛡️",
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000001003"),
        "name": "implant",
        "description": "Cybernetic implants and augments",
        "emoji": "🔌",
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000001004"),
        "name": "clothing",
        "description": "Basic clothing and apparel",
        "emoji": "👕",
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000001005"),
        "name": "consumable",
        "description": "Consumable items like potions and medkits",
        "emoji": "🧪",
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000001006"),
        "name": "tool",
        "description": "Utility tools and gadgets",
        "emoji": "🔧",
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000001007"),
        "name": "accessory",
        "description": "Accessories like jewelry and trinkets",
        "emoji": "💍",
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000001008"),
        "name": "backpack",
        "description": "Backpacks and storage items that expand inventory",
        "emoji": "🎒",
    },
]

# Item Templates seed data
ITEM_TEMPLATES = [
    # Enforcer starting equipment
    {
        "id": UUID("00000000-0000-0000-0000-000000002001"),
        "name": "Heavy Armor",
        "description": "Sturdy combat armor providing excellent protection",
        "category_id": UUID("00000000-0000-0000-0000-000000001002"),
        "equippable_slots": ["chest"],
        "rarity": "common",
        "value": 50,
        "resource_bonuses": {"max_health": 20.0},
        "resource_regeneration_modifiers": {},
        "stat_bonuses": {},
        "stat_multipliers": {},
        "damage_bonuses": {},
        "damage_multipliers": {},
        "healing_bonuses": {},
        "inventory_slots_bonus": 0,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000002002"),
        "name": "Combat Boots",
        "description": "Reinforced boots for combat situations",
        "category_id": UUID("00000000-0000-0000-0000-000000001002"),
        "equippable_slots": ["feet"],
        "rarity": "common",
        "value": 30,
        "resource_bonuses": {"max_stamina": 10.0},
        "resource_regeneration_modifiers": {},
        "stat_bonuses": {},
        "stat_multipliers": {},
        "damage_bonuses": {},
        "damage_multipliers": {},
        "healing_bonuses": {},
        "inventory_slots_bonus": 0,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000002003"),
        "name": "Basic Weapon",
        "description": "A standard combat weapon",
        "category_id": UUID("00000000-0000-0000-0000-000000001001"),
        "equippable_slots": ["right_hand", "left_hand"],
        "rarity": "common",
        "value": 40,
        "resource_bonuses": {},
        "resource_regeneration_modifiers": {},
        "stat_bonuses": {},
        "stat_multipliers": {},
        "damage_bonuses": {"physical": 5.0},
        "damage_multipliers": {},
        "healing_bonuses": {},
        "inventory_slots_bonus": 0,
    },
    # Tech Wizard starting equipment
    {
        "id": UUID("00000000-0000-0000-0000-000000002004"),
        "name": "Tech Jacket",
        "description": "A jacket with integrated tech enhancements",
        "category_id": UUID("00000000-0000-0000-0000-000000001004"),
        "equippable_slots": ["chest"],
        "rarity": "common",
        "value": 60,
        "resource_bonuses": {},
        "resource_regeneration_modifiers": {"tech_power": {"bonus": 0.2, "multiplier": 1.0}},
        "stat_bonuses": {},
        "stat_multipliers": {},
        "damage_bonuses": {},
        "damage_multipliers": {},
        "healing_bonuses": {},
        "inventory_slots_bonus": 0,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000002005"),
        "name": "Cyberdeck",
        "description": "A portable computing device for hacking and tech manipulation",
        "category_id": UUID("00000000-0000-0000-0000-000000001003"),
        "equippable_slots": ["left_hand"],
        "rarity": "common",
        "value": 80,
        "resource_bonuses": {"max_tech_power": 15.0},
        "resource_regeneration_modifiers": {},
        "stat_bonuses": {},
        "stat_multipliers": {},
        "damage_bonuses": {},
        "damage_multipliers": {},
        "healing_bonuses": {},
        "inventory_slots_bonus": 0,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000002006"),
        "name": "Data Gloves",
        "description": "Gloves with data interface capabilities",
        "category_id": UUID("00000000-0000-0000-0000-000000001007"),
        "equippable_slots": ["left_hand", "right_hand"],
        "rarity": "common",
        "value": 45,
        "resource_bonuses": {},
        "resource_regeneration_modifiers": {},
        "stat_bonuses": {"INT": 2.0},
        "stat_multipliers": {},
        "damage_bonuses": {},
        "damage_multipliers": {},
        "healing_bonuses": {},
        "inventory_slots_bonus": 0,
    },
    # Smooth Talker starting equipment
    {
        "id": UUID("00000000-0000-0000-0000-000000002007"),
        "name": "Stylish Outfit",
        "description": "A fashionable outfit that enhances charisma",
        "category_id": UUID("00000000-0000-0000-0000-000000001004"),
        "equippable_slots": ["chest"],
        "rarity": "common",
        "value": 55,
        "resource_bonuses": {},
        "resource_regeneration_modifiers": {},
        "stat_bonuses": {"CHA": 3.0},
        "stat_multipliers": {},
        "damage_bonuses": {},
        "damage_multipliers": {},
        "healing_bonuses": {},
        "inventory_slots_bonus": 0,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000002008"),
        "name": "Charisma Implant",
        "description": "A cybernetic implant that enhances social presence",
        "category_id": UUID("00000000-0000-0000-0000-000000001003"),
        "equippable_slots": ["neck"],
        "rarity": "common",
        "value": 70,
        "resource_bonuses": {},
        "resource_regeneration_modifiers": {},
        "stat_bonuses": {},
        "stat_multipliers": {"CHA": 1.1},
        "damage_bonuses": {},
        "damage_multipliers": {},
        "healing_bonuses": {},
        "inventory_slots_bonus": 0,
    },
    # Spy starting equipment
    {
        "id": UUID("00000000-0000-0000-0000-000000002009"),
        "name": "Stealth Suit",
        "description": "A lightweight suit designed for stealth operations",
        "category_id": UUID("00000000-0000-0000-0000-000000001002"),
        "equippable_slots": ["chest"],
        "rarity": "common",
        "value": 65,
        "resource_bonuses": {},
        "resource_regeneration_modifiers": {},
        "stat_bonuses": {"DEX": 3.0},
        "stat_multipliers": {},
        "damage_bonuses": {},
        "damage_multipliers": {},
        "healing_bonuses": {},
        "inventory_slots_bonus": 0,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000002010"),
        "name": "Concealed Weapon",
        "description": "A small, easily hidden weapon",
        "category_id": UUID("00000000-0000-0000-0000-000000001001"),
        "equippable_slots": ["right_hand"],
        "rarity": "common",
        "value": 35,
        "resource_bonuses": {},
        "resource_regeneration_modifiers": {},
        "stat_bonuses": {},
        "stat_multipliers": {},
        "damage_bonuses": {"physical": 3.0},
        "damage_multipliers": {},
        "healing_bonuses": {},
        "inventory_slots_bonus": 0,
    },
    # Wild Card starting equipment
    {
        "id": UUID("00000000-0000-0000-0000-000000002011"),
        "name": "Mixed Gear",
        "description": "An eclectic mix of equipment",
        "category_id": UUID("00000000-0000-0000-0000-000000001004"),
        "equippable_slots": ["chest"],
        "rarity": "common",
        "value": 50,
        "resource_bonuses": {"max_health": 10.0, "max_stamina": 5.0},
        "resource_regeneration_modifiers": {},
        "stat_bonuses": {},
        "stat_multipliers": {},
        "damage_bonuses": {},
        "damage_multipliers": {},
        "healing_bonuses": {},
        "inventory_slots_bonus": 0,
    },
]

# Character Class Starting Equipment mappings
# Format: (character_class_id, item_template_id, equipment_slot, quantity)
CLASS_STARTING_EQUIPMENT = [
    # Enforcer: Heavy Armor (chest), Combat Boots (feet), Basic Weapon (right_hand)
    (
        UUID("00000000-0000-0000-0000-000000000001"),
        UUID("00000000-0000-0000-0000-000000002001"),
        "chest",
        1,
    ),
    (
        UUID("00000000-0000-0000-0000-000000000001"),
        UUID("00000000-0000-0000-0000-000000002002"),
        "feet",
        1,
    ),
    (
        UUID("00000000-0000-0000-0000-000000000001"),
        UUID("00000000-0000-0000-0000-000000002003"),
        "right_hand",
        1,
    ),
    # Tech Wizard: Tech Jacket (chest), Cyberdeck (left_hand), Data Gloves (right_hand)
    (
        UUID("00000000-0000-0000-0000-000000000002"),
        UUID("00000000-0000-0000-0000-000000002004"),
        "chest",
        1,
    ),
    (
        UUID("00000000-0000-0000-0000-000000000002"),
        UUID("00000000-0000-0000-0000-000000002005"),
        "left_hand",
        1,
    ),
    (
        UUID("00000000-0000-0000-0000-000000000002"),
        UUID("00000000-0000-0000-0000-000000002006"),
        "right_hand",
        1,
    ),
    # Smooth Talker: Stylish Outfit (chest), Charisma Implant (neck)
    (
        UUID("00000000-0000-0000-0000-000000000003"),
        UUID("00000000-0000-0000-0000-000000002007"),
        "chest",
        1,
    ),
    (
        UUID("00000000-0000-0000-0000-000000000003"),
        UUID("00000000-0000-0000-0000-000000002008"),
        "neck",
        1,
    ),
    # Spy: Stealth Suit (chest), Concealed Weapon (right_hand)
    (
        UUID("00000000-0000-0000-0000-000000000004"),
        UUID("00000000-0000-0000-0000-000000002009"),
        "chest",
        1,
    ),
    (
        UUID("00000000-0000-0000-0000-000000000004"),
        UUID("00000000-0000-0000-0000-000000002010"),
        "right_hand",
        1,
    ),
    # Wild Card: Mixed Gear (chest)
    (
        UUID("00000000-0000-0000-0000-000000000005"),
        UUID("00000000-0000-0000-0000-000000002011"),
        "chest",
        1,
    ),
]


async def seed_character_classes(
    postgres_manager: "PostgresManager",
) -> dict[UUID, CharacterClass]:
    """
    Seed character classes into the database.

    Args:
        postgres_manager: PostgreSQL manager instance

    Returns:
        Dictionary mapping character class IDs to CharacterClass instances
    """
    from ds_common.repository.character_class import CharacterClassRepository

    logger.info("Seeding character classes...")
    repo = CharacterClassRepository(postgres_manager)
    seeded_classes: dict[UUID, CharacterClass] = {}

    for class_data in CHARACTER_CLASSES:
        class_id = class_data["id"]
        existing = await repo.get_by_id(class_id)
        if existing:
            logger.debug(f"Character class '{class_data['name']}' already exists, skipping")
            seeded_classes[class_id] = existing
            continue

        character_class = CharacterClass(
            id=class_id,
            name=class_data["name"],
            description=class_data["description"],
            emoji=class_data["emoji"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        created = await repo.create(character_class)
        seeded_classes[class_id] = created
        logger.info(f"Created character class: {class_data['name']}")

    return seeded_classes


async def seed_character_stats(
    postgres_manager: "PostgresManager",
) -> dict[UUID, CharacterStat]:
    """
    Seed character stats into the database.

    Args:
        postgres_manager: PostgreSQL manager instance

    Returns:
        Dictionary mapping character stat IDs to CharacterStat instances
    """
    from ds_common.repository.character_stat import CharacterStatRepository

    logger.info("Seeding character stats...")
    repo = CharacterStatRepository(postgres_manager)
    seeded_stats: dict[UUID, CharacterStat] = {}

    for stat_data in CHARACTER_STATS:
        stat_id = stat_data["id"]
        existing = await repo.get_by_id(stat_id)
        if existing:
            logger.debug(f"Character stat '{stat_data['name']}' already exists, skipping")
            seeded_stats[stat_id] = existing
            continue

        character_stat = CharacterStat(
            id=stat_id,
            name=stat_data["name"],
            abbr=stat_data["abbr"],
            description=stat_data["description"],
            emoji=stat_data["emoji"],
            max_value=stat_data["max_value"],
            is_primary=stat_data["is_primary"],
            is_mutable=stat_data["is_mutable"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        created = await repo.create(character_stat)
        seeded_stats[stat_id] = created
        logger.info(f"Created character stat: {stat_data['name']}")

    return seeded_stats


async def seed_class_stat_relationships(
    postgres_manager: "PostgresManager",
    character_classes: dict[UUID, CharacterClass],
    character_stats: dict[UUID, CharacterStat],
) -> None:
    """
    Seed character class to stat relationships.

    Args:
        postgres_manager: PostgreSQL manager instance
        character_classes: Dictionary of seeded character classes
        character_stats: Dictionary of seeded character stats
    """
    from sqlmodel import select

    from ds_common.models.junction_tables import CharacterClassStat

    logger.info("Seeding character class to stat relationships...")

    async with postgres_manager.get_session() as session:
        for class_id, stat_id in CLASS_STAT_RELATIONSHIPS:
            # Check if relationship already exists
            stmt = select(CharacterClassStat).where(
                CharacterClassStat.character_class_id == class_id,
                CharacterClassStat.character_stat_id == stat_id,
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                logger.debug(
                    f"Relationship {character_classes[class_id].name} -> {character_stats[stat_id].name} already exists, skipping"
                )
                continue

            # Create relationship
            relationship = CharacterClassStat(
                character_class_id=class_id,
                character_stat_id=stat_id,
            )
            session.add(relationship)
            await session.commit()
            logger.info(
                f"Created relationship: {character_classes[class_id].name} -> {character_stats[stat_id].name}"
            )


async def seed_item_categories(
    postgres_manager: "PostgresManager",
) -> dict[UUID, ItemCategory]:
    """
    Seed item categories into the database.

    Args:
        postgres_manager: PostgreSQL manager instance

    Returns:
        Dictionary mapping item category IDs to ItemCategory instances
    """
    from ds_common.repository.item_category import ItemCategoryRepository

    logger.info("Seeding item categories...")
    repo = ItemCategoryRepository(postgres_manager)
    seeded_categories: dict[UUID, ItemCategory] = {}

    for category_data in ITEM_CATEGORIES:
        category_id = category_data["id"]
        existing = await repo.get_by_id(category_id)
        if existing:
            logger.debug(f"Item category '{category_data['name']}' already exists, skipping")
            seeded_categories[category_id] = existing
            continue

        item_category = ItemCategory(
            id=category_id,
            name=category_data["name"],
            description=category_data["description"],
            emoji=category_data["emoji"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        created = await repo.create(item_category)
        seeded_categories[category_id] = created
        logger.info(f"Created item category: {category_data['name']}")

    return seeded_categories


async def seed_item_templates(
    postgres_manager: "PostgresManager",
    item_categories: dict[UUID, ItemCategory],
) -> dict[UUID, ItemTemplate]:
    """
    Seed item templates into the database.

    Args:
        postgres_manager: PostgreSQL manager instance
        item_categories: Dictionary of seeded item categories

    Returns:
        Dictionary mapping item template IDs to ItemTemplate instances
    """
    from ds_common.repository.item_template import ItemTemplateRepository

    logger.info("Seeding item templates...")
    repo = ItemTemplateRepository(postgres_manager)
    seeded_templates: dict[UUID, ItemTemplate] = {}

    for template_data in ITEM_TEMPLATES:
        template_id = template_data["id"]
        existing = await repo.get_by_id(template_id)
        if existing:
            logger.debug(f"Item template '{template_data['name']}' already exists, skipping")
            seeded_templates[template_id] = existing
            continue

        item_template = ItemTemplate(
            id=template_id,
            name=template_data["name"],
            description=template_data["description"],
            category_id=template_data["category_id"],
            equippable_slots=template_data["equippable_slots"],
            rarity=template_data["rarity"],
            value=template_data["value"],
            stat_bonuses=template_data["stat_bonuses"],
            stat_multipliers=template_data["stat_multipliers"],
            resource_bonuses=template_data["resource_bonuses"],
            resource_regeneration_modifiers=template_data["resource_regeneration_modifiers"],
            damage_bonuses=template_data["damage_bonuses"],
            damage_multipliers=template_data["damage_multipliers"],
            healing_bonuses=template_data["healing_bonuses"],
            inventory_slots_bonus=template_data["inventory_slots_bonus"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        created = await repo.create(item_template)
        seeded_templates[template_id] = created
        logger.info(f"Created item template: {template_data['name']}")

    return seeded_templates


async def seed_class_starting_equipment(
    postgres_manager: "PostgresManager",
    character_classes: dict[UUID, CharacterClass],
    item_templates: dict[UUID, ItemTemplate],
) -> None:
    """
    Seed character class starting equipment relationships.

    Args:
        postgres_manager: PostgreSQL manager instance
        character_classes: Dictionary of seeded character classes
        item_templates: Dictionary of seeded item templates
    """
    from sqlmodel import select

    from ds_common.models.junction_tables import CharacterClassStartingEquipment

    logger.info("Seeding character class starting equipment...")

    async with postgres_manager.get_session() as session:
        for class_id, template_id, slot, quantity in CLASS_STARTING_EQUIPMENT:
            # Check if relationship already exists
            stmt = select(CharacterClassStartingEquipment).where(
                CharacterClassStartingEquipment.character_class_id == class_id,
                CharacterClassStartingEquipment.item_template_id == template_id,
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                logger.debug(
                    f"Starting equipment relationship {character_classes[class_id].name} -> {item_templates[template_id].name} already exists, skipping"
                )
                continue

            # Create relationship
            relationship = CharacterClassStartingEquipment(
                character_class_id=class_id,
                item_template_id=template_id,
                equipment_slot=slot,
                quantity=quantity,
            )
            session.add(relationship)
            await session.commit()
            logger.info(
                f"Created starting equipment: {character_classes[class_id].name} -> {item_templates[template_id].name} ({slot})"
            )


async def seed_all(postgres_manager: "PostgresManager") -> None:
    """
    Seed all game data into the database.

    Args:
        postgres_manager: PostgreSQL manager instance
    """
    logger.info("Starting database seeding...")

    character_classes = await seed_character_classes(postgres_manager)
    character_stats = await seed_character_stats(postgres_manager)
    await seed_class_stat_relationships(postgres_manager, character_classes, character_stats)

    item_categories = await seed_item_categories(postgres_manager)
    item_templates = await seed_item_templates(postgres_manager, item_categories)
    await seed_class_starting_equipment(postgres_manager, character_classes, item_templates)

    # World data seeding
    from ds_common.world_seed_data import seed_all_world_data

    await seed_all_world_data(postgres_manager)

    logger.info("Database seeding completed!")


if __name__ == "__main__":
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
            await seed_all(postgres_manager)
        finally:
            await postgres_manager.close()

    asyncio.run(main())
