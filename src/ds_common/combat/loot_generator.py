"""
Loot generation service for NPCs - contextual item and credit rewards.
"""

import logging
import random
import uuid
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ds_common.models.npc import NPC
    from ds_discord_bot.postgres_manager import PostgresManager

logger = logging.getLogger(__name__)

# Profession to item category mapping
PROFESSION_ITEM_MAPPING = {
    # Combat professions
    "Guard": ["weapon", "armor", "consumable"],
    "Enforcer": ["weapon", "armor", "consumable"],
    "Soldier": ["weapon", "armor", "consumable"],
    "Mercenary": ["weapon", "armor", "consumable"],
    "Bounty Hunter": ["weapon", "armor", "tool"],
    # Merchant professions
    "Merchant": ["consumable", "accessory", "tool"],
    "Trader": ["consumable", "accessory", "tool"],
    "Shopkeeper": ["consumable", "accessory"],
    # Tech professions
    "Technician": ["tool", "implant", "consumable"],
    "Engineer": ["tool", "implant", "consumable"],
    "Hacker": ["tool", "implant", "consumable"],
    "Mechanic": ["tool", "consumable"],
    # Faction-specific (will check faction separately)
    "Faction Member": ["weapon", "armor", "consumable"],
    # Default fallback
    "default": ["consumable", "tool", "accessory"],
}

# Rarity levels and level thresholds
RARITY_LEVELS = {
    "common": (1, 20),
    "uncommon": (10, 40),
    "rare": (30, 60),
    "epic": (50, 80),
    "legendary": (70, 100),
}


async def get_profession_item_pool(
    profession: str, level: int, postgres_manager: "PostgresManager"
) -> list[str]:
    """
    Get contextual item template names based on NPC profession and level.

    Args:
        profession: NPC profession
        level: NPC level
        postgres_manager: PostgreSQL manager for querying item templates

    Returns:
        List of item template names that match the profession and level
    """
    from ds_common.repository.item_category import ItemCategoryRepository
    from ds_common.repository.item_template import ItemTemplateRepository

    # Get categories for this profession
    categories = PROFESSION_ITEM_MAPPING.get(profession, PROFESSION_ITEM_MAPPING["default"])

    # Determine max rarity based on level
    max_rarity = "common"
    for rarity, (min_level, max_level) in RARITY_LEVELS.items():
        if min_level <= level <= max_level:
            max_rarity = rarity
            break
    if level > 80:
        max_rarity = "legendary"

    # Get rarity order for filtering
    rarity_order = ["common", "uncommon", "rare", "epic", "legendary"]
    max_rarity_index = rarity_order.index(max_rarity)
    allowed_rarities = rarity_order[: max_rarity_index + 1]

    # Query item templates
    category_repo = ItemCategoryRepository(postgres_manager)
    template_repo = ItemTemplateRepository(postgres_manager)

    item_names = []

    # Get all templates and filter
    all_templates = await template_repo.get_all()

    for template in all_templates:
        # Check category
        category = await category_repo.get_by_id(template.category_id)
        if not category or category.name not in categories:
            continue

        # Check rarity
        if template.rarity not in allowed_rarities:
            continue

        item_names.append(template.name)

    return item_names


async def select_random_items(
    pool: list[str], count: int, level: int, postgres_manager: "PostgresManager"
) -> list[dict]:
    """
    Select random items from pool and create item instances.

    Args:
        pool: List of item template names
        count: Number of items to select
        level: NPC level (for weighting)
        postgres_manager: PostgreSQL manager for querying templates

    Returns:
        List of item instance dicts
    """
    from ds_common.repository.item_template import ItemTemplateRepository

    if not pool:
        return []

    # Select random items (with replacement if pool is smaller than count)
    selected_names = random.choices(pool, k=min(count, len(pool)))

    template_repo = ItemTemplateRepository(postgres_manager)
    item_instances = []

    for name in selected_names:
        template = await template_repo.get_by_field("name", name, case_sensitive=False)
        if not template:
            continue

        # Create item instance
        instance_id = str(uuid.uuid4())
        item_instance = {
            "instance_id": instance_id,
            "item_template_id": str(template.id),
            "name": template.name,
            "quantity": 1,
            "equipped": False,
            "equipment_slot": None,
        }
        item_instances.append(item_instance)

    return item_instances


async def generate_npc_loot(
    npc: "NPC",
    loot_quality_multiplier: float = 1.0,
    postgres_manager: Optional["PostgresManager"] = None,
) -> dict:
    """
    Generate loot for an NPC based on their profession, faction, and level.

    Args:
        npc: NPC to generate loot for
        loot_quality_multiplier: Multiplier for loot quality (default 1.0)
        postgres_manager: PostgreSQL manager (required for item template queries)

    Returns:
        Dictionary with "items" (list of item dicts) and "credits" (int)
    """
    if not postgres_manager:
        logger.warning("No postgres_manager provided, returning empty loot")
        return {"items": [], "credits": 0}

    # Calculate credits (scaled by level)
    base_credits = random.randint(npc.level * 10, npc.level * 50)
    credits = int(base_credits * loot_quality_multiplier)

    # Determine number of items (1-3 based on level)
    if npc.level < 10:
        item_count = random.randint(1, 2)
    elif npc.level < 30:
        item_count = random.randint(1, 3)
    else:
        item_count = random.randint(2, 3)

    # Get profession-based item pool
    profession = npc.profession or "default"
    item_pool = await get_profession_item_pool(profession, npc.level, postgres_manager)

    # If faction exists, add faction-specific items (could expand this)
    if npc.faction:
        # For now, just add more combat items for faction members
        faction_pool = await get_profession_item_pool("Faction Member", npc.level, postgres_manager)
        item_pool.extend(faction_pool)

    # Select random items
    items = await select_random_items(item_pool, item_count, npc.level, postgres_manager)

    logger.debug(
        f"Generated loot for {npc.name} (level {npc.level}, {profession}): "
        f"{len(items)} items, {credits} credits"
    )

    return {"items": items, "credits": credits}
