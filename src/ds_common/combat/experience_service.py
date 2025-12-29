"""
Experience and leveling service for character progression.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ds_common.models.character import Character

logger = logging.getLogger(__name__)


def calculate_experience_reward(npc_level: int, character_level: int) -> int:
    """
    Calculate experience points rewarded for defeating an NPC.

    Formula scales based on level difference:
    - If NPC is higher level: 100 * npc_level * (1 + (npc_level - character_level) * 0.1)
    - If NPC is lower level: 50 * npc_level (minimum reward)

    Args:
        npc_level: Level of the defeated NPC
        character_level: Level of the character receiving the reward

    Returns:
        Experience points to award
    """
    level_diff = npc_level - character_level

    if level_diff > 0:
        # NPC is higher level - bonus experience
        exp = int(100 * npc_level * (1 + level_diff * 0.1))
    else:
        # NPC is same or lower level - base experience
        exp = 50 * npc_level

    # Ensure minimum of 1 exp
    return max(1, exp)


def calculate_exp_for_level(level: int) -> int:
    """
    Calculate total experience required to reach a given level.

    Uses exponential formula: 1000 * (level ** 2)
    - Level 1: 0 exp (starting level)
    - Level 2: 4000 exp (1000 * 2^2)
    - Level 3: 9000 exp (1000 * 3^2)
    - Level 4: 16000 exp (1000 * 4^2)

    Args:
        level: Target level

    Returns:
        Total experience required to reach that level
    """
    if level <= 1:
        return 0
    return int(1000 * (level**2))


def add_experience(character: "Character", exp_amount: int) -> tuple["Character", bool]:
    """
    Add experience to a character and check for level up.

    Args:
        character: Character to add experience to
        exp_amount: Amount of experience to add

    Returns:
        Tuple of (updated_character, leveled_up)
        - updated_character: Character with updated exp (and level if leveled up)
        - leveled_up: True if character leveled up, False otherwise
    """
    if exp_amount <= 0:
        return character, False

    character.exp += exp_amount
    leveled_up = False

    # Check for level ups (can level multiple times if enough exp)
    while True:
        exp_for_next = calculate_exp_for_level(character.level + 1)
        if character.exp >= exp_for_next:
            character.level += 1
            leveled_up = True
            logger.info(f"Character {character.name} leveled up to level {character.level}")
        else:
            break

    return character, leveled_up


def apply_level_up(character: "Character") -> "Character":
    """
    Apply level up benefits to a character.

    Benefits:
    - +2 to all stats (STR, DEX, INT, PER, CHA, LUK)
    - Max resources are recalculated (should be done via initialize_combat_resources)
    - Current resources restored to max

    Note: This function only updates stats. Resource recalculation should be done
    separately via CharacterRepository.initialize_combat_resources() to include
    equipment bonuses.

    Args:
        character: Character that leveled up

    Returns:
        Updated character with stat increases
    """
    # Add +2 to all stats
    stat_names = ["STR", "DEX", "INT", "PER", "CHA", "LUK"]
    for stat in stat_names:
        current_value = character.stats.get(stat, 0)
        character.stats[stat] = current_value + 2

    logger.info(f"Applied level up benefits to {character.name}: +2 to all stats")

    return character
