"""
Encounter-related AI tools for managing game encounters, rewards, and corpse searching.
"""

from uuid import UUID

from pydantic_ai import RunContext

from ds_common.combat.experience_service import calculate_experience_reward
from ds_common.combat.loot_generator import generate_npc_loot
from ds_common.models.character import Character
from ds_common.models.encounter import Encounter, EncounterStatus, EncounterType
from ds_common.models.game_master import (
    GMAgentDependencies,
    RequestDistributeRewards,
    RequestEndEncounter,
    RequestSearchCorpse,
    RequestStartEncounter,
    ResponseDistributeRewards,
    ResponseEncounterStatus,
    ResponseSearchCorpse,
)
from ds_common.models.game_session import GameSession
from ds_common.models.junction_tables import EncounterCharacter, EncounterNPC
from ds_common.repository.character import CharacterRepository
from ds_common.repository.encounter import EncounterRepository
from ds_common.repository.npc import NPCRepository


async def start_encounter(
    ctx: RunContext[GMAgentDependencies],
    request: RequestStartEncounter,
) -> ResponseEncounterStatus:
    """Start a new encounter in a game session.

    Args:
        ctx: The context of the agent.
        request: The request to start an encounter.

    Returns:
        ResponseEncounterStatus: The created encounter's status.
    """
    postgres_manager = ctx.deps.postgres_manager
    encounter_repository = EncounterRepository(postgres_manager)

    # Map encounter type string to enum
    encounter_type_map = {
        "combat": EncounterType.COMBAT,
        "social": EncounterType.SOCIAL,
        "environmental_hazard": EncounterType.ENVIRONMENTAL_HAZARD,
    }
    encounter_type = encounter_type_map.get(
        request.encounter_type.lower(), EncounterType.COMBAT
    )

    # Create encounter
    encounter = Encounter(
        game_session_id=request.game_session.id,
        encounter_type=encounter_type,
        status=EncounterStatus.ACTIVE,
        description=request.description,
    )

    encounter = await encounter_repository.create(encounter)

    print(f"!!! Started encounter: {encounter.id} ({encounter_type.value})")

    return ResponseEncounterStatus(
        encounter_id=str(encounter.id),
        encounter_type=encounter_type.value,
        status=encounter.status.value,
        description=encounter.description,
        character_count=0,
        npc_count=0,
    )


async def end_encounter(
    ctx: RunContext[GMAgentDependencies],
    request: RequestEndEncounter,
) -> ResponseEncounterStatus:
    """End an active encounter.

    Args:
        ctx: The context of the agent.
        request: The request to end an encounter.

    Returns:
        ResponseEncounterStatus: The ended encounter's status.
    """
    postgres_manager = ctx.deps.postgres_manager
    encounter_repository = EncounterRepository(postgres_manager)

    encounter = await encounter_repository.get_by_id(UUID(request.encounter_id))
    if not encounter:
        raise ValueError(f"Encounter {request.encounter_id} not found")

    # Check and mark any dead NPCs before ending
    encounter = await encounter_repository.check_and_mark_dead_npcs(encounter)

    encounter = await encounter_repository.end_encounter(encounter)

    print(f"!!! Ended encounter: {encounter.id}")

    return ResponseEncounterStatus(
        encounter_id=str(encounter.id),
        encounter_type=encounter.encounter_type.value,
        status=encounter.status.value,
        description=encounter.description,
        character_count=len(encounter.characters) if encounter.characters else 0,
        npc_count=len(encounter.npcs) if encounter.npcs else 0,
    )


async def get_encounter_status(
    ctx: RunContext[GMAgentDependencies],
    game_session: GameSession,
) -> ResponseEncounterStatus | None:
    """Get the status of the active encounter in a game session.

    Args:
        ctx: The context of the agent.
        game_session: The game session to check.

    Returns:
        ResponseEncounterStatus: The active encounter's status, or None if no active encounter.
    """
    postgres_manager = ctx.deps.postgres_manager
    encounter_repository = EncounterRepository(postgres_manager)

    encounter = await encounter_repository.get_active_encounter(game_session)
    if not encounter:
        return None

    return ResponseEncounterStatus(
        encounter_id=str(encounter.id),
        encounter_type=encounter.encounter_type.value,
        status=encounter.status.value,
        description=encounter.description,
        character_count=len(encounter.characters) if encounter.characters else 0,
        npc_count=len(encounter.npcs) if encounter.npcs else 0,
    )


async def distribute_encounter_rewards(
    ctx: RunContext[GMAgentDependencies],
    request: RequestDistributeRewards,
) -> ResponseDistributeRewards:
    """Distribute experience rewards to all characters who participated in an encounter.

    Args:
        ctx: The context of the agent.
        request: The request to distribute rewards.

    Returns:
        ResponseDistributeRewards: Summary of rewards distributed.
    """
    postgres_manager = ctx.deps.postgres_manager
    encounter_repository = EncounterRepository(postgres_manager)
    character_repository = CharacterRepository(postgres_manager)
    npc_repository = NPCRepository(postgres_manager)

    encounter = await encounter_repository.get_by_id(UUID(request.encounter_id))
    if not encounter:
        raise ValueError(f"Encounter {request.encounter_id} not found")

    # Check if rewards already distributed
    if encounter.rewards_distributed:
        return ResponseDistributeRewards(
            encounter_id=str(encounter.id),
            characters_rewarded=[],
            total_exp_distributed=0,
            message="Rewards have already been distributed for this encounter.",
        )

    # Check and mark dead NPCs
    encounter = await encounter_repository.check_and_mark_dead_npcs(encounter)

    # Get all dead NPCs
    dead_npc_ids = encounter.dead_npcs or []
    if not dead_npc_ids:
        return ResponseDistributeRewards(
            encounter_id=str(encounter.id),
            characters_rewarded=[],
            total_exp_distributed=0,
            message="No NPCs were defeated in this encounter.",
        )

    # Get all participating characters
    from sqlalchemy.ext.asyncio import AsyncSession

    async def _refresh(sess: AsyncSession):
        await sess.refresh(encounter, ["characters"])

    await encounter_repository._with_session(_refresh, None)
    characters = encounter.characters or []
    if not characters:
        return ResponseDistributeRewards(
            encounter_id=str(encounter.id),
            characters_rewarded=[],
            total_exp_distributed=0,
            message="No characters participated in this encounter.",
        )

    # Calculate total EXP for each character (shared equally)
    characters_rewarded = []
    total_exp_distributed = 0

    for npc_id in dead_npc_ids:
        npc = await npc_repository.get_by_id(npc_id)
        if not npc:
            continue

        # Calculate EXP per character (shared equally)
        for character in characters:
            exp_per_npc = calculate_experience_reward(npc.level, character.level)
            exp_per_character = exp_per_npc // len(characters)  # Share equally
            if exp_per_character > 0:
                character, leveled_up = await character_repository.add_experience(
                    character, exp_per_character
                )
                total_exp_distributed += exp_per_character

                # Track this character's rewards
                char_reward = next(
                    (
                        cr
                        for cr in characters_rewarded
                        if cr["character_id"] == str(character.id)
                    ),
                    None,
                )
                if not char_reward:
                    char_reward = {
                        "character_id": str(character.id),
                        "character_name": character.name,
                        "exp_gained": 0,
                        "leveled_up": False,
                        "new_level": character.level,
                    }
                    characters_rewarded.append(char_reward)

                char_reward["exp_gained"] += exp_per_character
                if leveled_up:
                    char_reward["leveled_up"] = True
                    char_reward["new_level"] = character.level

    # Mark rewards as distributed
    encounter.rewards_distributed = True
    await encounter_repository.update(encounter)

    # Build message
    reward_summary = []
    for char_reward in characters_rewarded:
        level_msg = (
            f" (Leveled up to {char_reward['new_level']}!)" if char_reward["leveled_up"] else ""
        )
        reward_summary.append(
            f"{char_reward['character_name']}: +{char_reward['exp_gained']} EXP{level_msg}"
        )

    message = f"Distributed {total_exp_distributed} total EXP. " + "; ".join(reward_summary)

    print(f"!!! Distributed rewards for encounter {encounter.id}: {total_exp_distributed} EXP")

    return ResponseDistributeRewards(
        encounter_id=str(encounter.id),
        characters_rewarded=characters_rewarded,
        total_exp_distributed=total_exp_distributed,
        message=message,
    )


async def search_corpse(
    ctx: RunContext[GMAgentDependencies],
    request: RequestSearchCorpse,
) -> ResponseSearchCorpse:
    """Search a dead NPC's corpse for loot.

    Args:
        ctx: The context of the agent.
        request: The request to search a corpse.

    Returns:
        ResponseSearchCorpse: Loot found from the corpse.
    """
    postgres_manager = ctx.deps.postgres_manager
    character_repository = CharacterRepository(postgres_manager)
    npc_repository = NPCRepository(postgres_manager)
    encounter_repository = EncounterRepository(postgres_manager)

    # Get character (use action_character if available, otherwise from request)
    character = ctx.deps.action_character
    if not character and request.character_id:
        character = await character_repository.get_by_id(UUID(request.character_id))
    if not character:
        raise ValueError("No character available to search corpse")

    # Get NPC
    npc = await npc_repository.get_by_id(UUID(request.npc_id))
    if not npc:
        raise ValueError(f"NPC {request.npc_id} not found")

    # Find the encounter this NPC belongs to (if any)
    all_encounters = await encounter_repository.get_all()
    encounter = None
    for enc in all_encounters:
        await encounter_repository._with_session(
            lambda sess: sess.refresh(enc, ["npcs"]), None
        )
        if enc.npcs and any(n.id == npc.id for n in enc.npcs):
            encounter = enc
            break

    if not encounter:
        raise ValueError(f"NPC {request.npc_id} is not part of any encounter")

    # Check if NPC is dead
    if not npc.is_incapacitated:
        return ResponseSearchCorpse(
            npc_id=str(npc.id),
            character_id=str(character.id),
            items_found=[],
            credits_found=0,
            message=f"{npc.name} is not dead and cannot be searched.",
        )

    # Check if NPC has already been searched
    if encounter.searched_npcs and npc.id in encounter.searched_npcs:
        return ResponseSearchCorpse(
            npc_id=str(npc.id),
            character_id=str(character.id),
            items_found=[],
            credits_found=0,
            message=f"{npc.name}'s corpse has already been searched.",
        )

    # Generate loot
    loot = await generate_npc_loot(
        npc, loot_quality_multiplier=1.0, postgres_manager=postgres_manager
    )

    # Add items to character inventory
    inventory = character.inventory or []
    for item in loot["items"]:
        inventory.append(item)

    # Add credits
    character.credits += loot["credits"]
    character.inventory = inventory
    await character_repository.update(character)

    # Mark NPC as searched
    encounter = await encounter_repository.mark_npc_searched(encounter, npc.id)

    # Build message
    item_names = [item.get("name", "Unknown item") for item in loot["items"]]
    if item_names:
        items_msg = f"Found items: {', '.join(item_names)}. "
    else:
        items_msg = ""
    credits_msg = f"Found {loot['credits']} credits." if loot["credits"] > 0 else ""

    message = f"{items_msg}{credits_msg}".strip()
    if not message:
        message = "Found nothing of value."

    print(
        f"!!! {character.name} searched {npc.name}: {len(loot['items'])} items, {loot['credits']} credits"
    )

    return ResponseSearchCorpse(
        npc_id=str(npc.id),
        character_id=str(character.id),
        items_found=loot["items"],
        credits_found=loot["credits"],
        message=message,
    )


async def add_character_to_encounter(
    ctx: RunContext[GMAgentDependencies],
    encounter_id: str,
    character: Character,
) -> ResponseEncounterStatus:
    """Add a character to an active encounter.

    Args:
        ctx: The context of the agent.
        encounter_id: The encounter ID to add the character to.
        character: The character to add to the encounter.

    Returns:
        ResponseEncounterStatus: The updated encounter status.
    """
    postgres_manager = ctx.deps.postgres_manager
    encounter_repository = EncounterRepository(postgres_manager)
    character_repository = CharacterRepository(postgres_manager)

    encounter = await encounter_repository.get_by_id(UUID(encounter_id))
    if not encounter:
        raise ValueError(f"Encounter {encounter_id} not found")

    if encounter.status != EncounterStatus.ACTIVE:
        raise ValueError(f"Encounter {encounter_id} is not active")

    # Get fresh character
    character = await character_repository.get_by_id(character.id)
    if not character:
        raise ValueError(f"Character {character.id} not found")

    # Add character to encounter via junction table
    from sqlalchemy.ext.asyncio import AsyncSession

    async def _add_character(sess: AsyncSession):
        from sqlmodel import select

        # Check if already in encounter
        stmt = select(EncounterCharacter).where(
            EncounterCharacter.encounter_id == encounter.id,
            EncounterCharacter.character_id == character.id,
        )
        result = await sess.execute(stmt)
        if result.scalar_one_or_none():
            return  # Already in encounter

        # Create junction table entry
        junction = EncounterCharacter(
            encounter_id=encounter.id, character_id=character.id
        )
        sess.add(junction)
        await sess.commit()

    await encounter_repository._with_session(_add_character, None)

    # Refresh encounter to get updated character count
    await encounter_repository._with_session(
        lambda sess: sess.refresh(encounter, ["characters"]), None
    )

    print(f"!!! Added character {character.name} to encounter {encounter.id}")

    return ResponseEncounterStatus(
        encounter_id=str(encounter.id),
        encounter_type=encounter.encounter_type.value,
        status=encounter.status.value,
        description=encounter.description,
        character_count=len(encounter.characters) if encounter.characters else 0,
        npc_count=len(encounter.npcs) if encounter.npcs else 0,
    )


async def remove_character_from_encounter(
    ctx: RunContext[GMAgentDependencies],
    encounter_id: str,
    character: Character,
) -> ResponseEncounterStatus:
    """Remove a character from an active encounter.

    Args:
        ctx: The context of the agent.
        encounter_id: The encounter ID to remove the character from.
        character: The character to remove from the encounter.

    Returns:
        ResponseEncounterStatus: The updated encounter status.
    """
    postgres_manager = ctx.deps.postgres_manager
    encounter_repository = EncounterRepository(postgres_manager)

    encounter = await encounter_repository.get_by_id(UUID(encounter_id))
    if not encounter:
        raise ValueError(f"Encounter {encounter_id} not found")

    # Remove character from encounter via junction table
    from sqlalchemy.ext.asyncio import AsyncSession

    async def _remove_character(sess: AsyncSession):
        from sqlmodel import select, delete

        stmt = delete(EncounterCharacter).where(
            EncounterCharacter.encounter_id == encounter.id,
            EncounterCharacter.character_id == character.id,
        )
        await sess.execute(stmt)
        await sess.commit()

    await encounter_repository._with_session(_remove_character, None)

    # Refresh encounter to get updated character count
    await encounter_repository._with_session(
        lambda sess: sess.refresh(encounter, ["characters"]), None
    )

    print(f"!!! Removed character {character.name} from encounter {encounter.id}")

    return ResponseEncounterStatus(
        encounter_id=str(encounter.id),
        encounter_type=encounter.encounter_type.value,
        status=encounter.status.value,
        description=encounter.description,
        character_count=len(encounter.characters) if encounter.characters else 0,
        npc_count=len(encounter.npcs) if encounter.npcs else 0,
    )


async def add_npc_to_encounter(
    ctx: RunContext[GMAgentDependencies],
    encounter_id: str,
    npc_id: str,
) -> ResponseEncounterStatus:
    """Add an NPC to an active encounter.

    Args:
        ctx: The context of the agent.
        encounter_id: The encounter ID to add the NPC to.
        npc_id: The NPC ID to add to the encounter.

    Returns:
        ResponseEncounterStatus: The updated encounter status.
    """
    postgres_manager = ctx.deps.postgres_manager
    encounter_repository = EncounterRepository(postgres_manager)
    npc_repository = NPCRepository(postgres_manager)

    encounter = await encounter_repository.get_by_id(UUID(encounter_id))
    if not encounter:
        raise ValueError(f"Encounter {encounter_id} not found")

    if encounter.status != EncounterStatus.ACTIVE:
        raise ValueError(f"Encounter {encounter_id} is not active")

    npc = await npc_repository.get_by_id(UUID(npc_id))
    if not npc:
        raise ValueError(f"NPC {npc_id} not found")

    # Add NPC to encounter via junction table
    from sqlalchemy.ext.asyncio import AsyncSession

    async def _add_npc(sess: AsyncSession):
        from sqlmodel import select

        # Check if already in encounter
        stmt = select(EncounterNPC).where(
            EncounterNPC.encounter_id == encounter.id,
            EncounterNPC.npc_id == npc.id,
        )
        result = await sess.execute(stmt)
        if result.scalar_one_or_none():
            return  # Already in encounter

        # Create junction table entry
        junction = EncounterNPC(encounter_id=encounter.id, npc_id=npc.id)
        sess.add(junction)
        await sess.commit()

    await encounter_repository._with_session(_add_npc, None)

    # Refresh encounter to get updated NPC count
    await encounter_repository._with_session(
        lambda sess: sess.refresh(encounter, ["npcs"]), None
    )

    print(f"!!! Added NPC {npc.name} to encounter {encounter.id}")

    return ResponseEncounterStatus(
        encounter_id=str(encounter.id),
        encounter_type=encounter.encounter_type.value,
        status=encounter.status.value,
        description=encounter.description,
        character_count=len(encounter.characters) if encounter.characters else 0,
        npc_count=len(encounter.npcs) if encounter.npcs else 0,
    )


async def remove_npc_from_encounter(
    ctx: RunContext[GMAgentDependencies],
    encounter_id: str,
    npc_id: str,
) -> ResponseEncounterStatus:
    """Remove an NPC from an active encounter.

    Args:
        ctx: The context of the agent.
        encounter_id: The encounter ID to remove the NPC from.
        npc_id: The NPC ID to remove from the encounter.

    Returns:
        ResponseEncounterStatus: The updated encounter status.
    """
    postgres_manager = ctx.deps.postgres_manager
    encounter_repository = EncounterRepository(postgres_manager)

    encounter = await encounter_repository.get_by_id(UUID(encounter_id))
    if not encounter:
        raise ValueError(f"Encounter {encounter_id} not found")

    # Remove NPC from encounter via junction table
    from sqlalchemy.ext.asyncio import AsyncSession

    async def _remove_npc(sess: AsyncSession):
        from sqlmodel import delete

        stmt = delete(EncounterNPC).where(
            EncounterNPC.encounter_id == encounter.id,
            EncounterNPC.npc_id == UUID(npc_id),
        )
        await sess.execute(stmt)
        await sess.commit()

    await encounter_repository._with_session(_remove_npc, None)

    # Refresh encounter to get updated NPC count
    await encounter_repository._with_session(
        lambda sess: sess.refresh(encounter, ["npcs"]), None
    )

    print(f"!!! Removed NPC {npc_id} from encounter {encounter.id}")

    return ResponseEncounterStatus(
        encounter_id=str(encounter.id),
        encounter_type=encounter.encounter_type.value,
        status=encounter.status.value,
        description=encounter.description,
        character_count=len(encounter.characters) if encounter.characters else 0,
        npc_count=len(encounter.npcs) if encounter.npcs else 0,
    )


async def abandon_encounter(
    ctx: RunContext[GMAgentDependencies],
    encounter_id: str,
) -> ResponseEncounterStatus:
    """Abandon an active encounter (set status to ABANDONED).

    Args:
        ctx: The context of the agent.
        encounter_id: The encounter ID to abandon.

    Returns:
        ResponseEncounterStatus: The abandoned encounter's status.
    """
    postgres_manager = ctx.deps.postgres_manager
    encounter_repository = EncounterRepository(postgres_manager)

    encounter = await encounter_repository.get_by_id(UUID(encounter_id))
    if not encounter:
        raise ValueError(f"Encounter {encounter_id} not found")

    if encounter.status != EncounterStatus.ACTIVE:
        raise ValueError(f"Encounter {encounter_id} is not active")

    # Set status to ABANDONED
    from sqlalchemy.ext.asyncio import AsyncSession

    async def _abandon(sess: AsyncSession):
        encounter.status = EncounterStatus.ABANDONED
        sess.add(encounter)
        await sess.commit()
        await sess.refresh(encounter)

    await encounter_repository._with_session(_abandon, None)

    print(f"!!! Abandoned encounter: {encounter.id}")

    return ResponseEncounterStatus(
        encounter_id=str(encounter.id),
        encounter_type=encounter.encounter_type.value,
        status=encounter.status.value,
        description=encounter.description,
        character_count=len(encounter.characters) if encounter.characters else 0,
        npc_count=len(encounter.npcs) if encounter.npcs else 0,
    )

