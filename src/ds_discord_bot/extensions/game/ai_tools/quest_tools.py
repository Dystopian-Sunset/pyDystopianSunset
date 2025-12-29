"""
Quest-related AI tools for managing character quests.
"""

import uuid

from pydantic_ai import RunContext

from ds_common.models.game_master import (
    GMAgentDependencies,
    RequestGetQuests,
    RequestRemoveQuest,
    ResponseQuests,
    ResponseRemoveQuest,
)
from ds_common.models.quest import Quest
from ds_common.repository.character import CharacterRepository
from ds_common.repository.quest import QuestRepository

from .base import get_character_from_context


async def add_character_quest(
    ctx: RunContext[GMAgentDependencies],
    quest: Quest,
    items: list[dict] | None = None,
) -> None:
    """
    When an NPC or other entity offers a quest to the player, call this tool to add the quest to the character.

    **Quest Items**: Many quests come with items that the player must deliver, use, or return. Examples:
    - Delivery quests: "Deliver this package to [NPC/Location]"
    - Item retrieval: "Retrieve this key and bring it to [location]"
    - Escort missions: "Protect this item until you reach [destination]"

    If the quest comes with items, provide them in the items parameter:
    - Format: [{'name': 'Item Name', 'quantity': 1, 'type': 'QUEST_ITEM'}]
    - These items will be automatically added to the character's inventory
    - Items given with quests are tracked and will be automatically removed if the quest is abandoned
    - This creates interesting gameplay dynamics where abandoning a quest has consequences

    **Lifecycle Management**: The system automatically tracks which items belong to which quest. When a quest is:
    - Abandoned: All quest items are removed from inventory
    - Completed: Quest items remain in inventory (you may want to remove them manually if appropriate)

    Args:
        ctx: The context of the agent.
        quest: The quest to add.
        items: Optional list of items given with the quest. Format: [{'name': 'Item Name', 'quantity': 1, 'type': 'QUEST_ITEM'}]
    """
    character = ctx.deps.action_character
    if not character:
        raise ValueError("No action character available")

    postgres_manager = ctx.deps.postgres_manager

    character_repository = CharacterRepository(postgres_manager)
    character = await character_repository.get_by_id(character.id)

    if not character:
        raise ValueError(f"Character {character.id} not found")

    quest_repository = QuestRepository(postgres_manager)

    # Check if quest exists in database, create if it doesn't
    if not quest.id:
        # Quest doesn't exist yet, create it first
        created_quest = await quest_repository.create(quest)
        quest = created_quest
    else:
        # Check if quest exists
        existing_quest = await quest_repository.get_by_id(quest.id)
        if not existing_quest:
            # Quest with this ID doesn't exist, create it
            created_quest = await quest_repository.create(quest)
            quest = created_quest

    # Add items to inventory if provided, and track them
    items_given = []
    if items:
        inventory = character.inventory if character.inventory else []

        for item_data in items:
            item_name = item_data.get("name")
            item_quantity = item_data.get("quantity", 1)
            item_type = item_data.get("type", "QUEST_ITEM")

            # Generate instance_id for tracking
            instance_id = str(uuid.uuid4())

            # Create item entry
            item_entry = {
                "instance_id": instance_id,
                "name": item_name,
                "quantity": item_quantity,
                "type": item_type,
                "equipped": False,
                "equipment_slot": None,
            }

            # Add to inventory (merge quantities if item already exists)
            item_found = False
            for inv_item in inventory:
                if inv_item.get("name") == item_name:
                    inv_item["quantity"] = inv_item.get("quantity", 0) + item_quantity
                    # Update instance_id if not set
                    if "instance_id" not in inv_item:
                        inv_item["instance_id"] = instance_id
                    item_found = True
                    break

            if not item_found:
                inventory.append(item_entry)

            # Track item for quest abandonment
            items_given.append(
                {
                    "name": item_name,
                    "quantity": item_quantity,
                    "instance_id": instance_id,
                }
            )

        character.inventory = inventory
        await character_repository.update(character)

    # Get session ID from context for tracking
    session_id = ctx.deps.game_session.id if ctx.deps.game_session else None

    # Now add the relationship with tracked items and session_id
    await quest_repository.add_character_quest(
        character, quest, items_given=items_given, session_id=session_id
    )

    # Track quest items in session memory (if memory system is available)
    if items_given and session_id:
        try:
            from openai import AsyncOpenAI

            from ds_common.config_bot import get_config
            from ds_common.memory.memory_processor import MemoryProcessor

            config = get_config()
            embedding_base_url = config.ai_embedding_base_url
            embedding_api_key = config.ai_embedding_api_key

            if embedding_base_url or embedding_api_key:
                client_kwargs = {
                    "api_key": embedding_api_key
                    if embedding_api_key
                    else "sk-ollama-local-dummy-key-not-used"
                }
                if embedding_base_url:
                    client_kwargs["base_url"] = embedding_base_url

                openai_client = AsyncOpenAI(**client_kwargs)
                embedding_model = config.ai_embedding_model
                embedding_dimensions = config.ai_embedding_dimensions

                memory_processor = MemoryProcessor(
                    postgres_manager,
                    openai_client,
                    redis_client=None,  # Redis optional for memory tracking
                    embedding_model=embedding_model,
                    embedding_dimensions=embedding_dimensions,
                )

                # Track quest items in session memory
                item_names = [item["name"] for item in items_given]
                await memory_processor.capture_session_event(
                    session_id=session_id,
                    character_id=character.id,
                    memory_type="action",
                    content={
                        "action": "quest_accepted_with_items",
                        "quest_name": quest.name,
                        "items_received": item_names,
                        "items_data": items_given,  # Store full item data for cleanup
                        "description": f"Accepted quest '{quest.name}' and received items: {', '.join(item_names)}",
                    },
                )
        except Exception as e:
            # Don't fail if memory tracking fails
            print(f"!!! Failed to track quest items in session memory: {e}")

    print(f"!!! Added quest: {quest.name} with {len(items_given)} items")


async def get_character_quests(
    ctx: RunContext[GMAgentDependencies],
    request: RequestGetQuests,
) -> ResponseQuests:
    """
    **CRITICAL TOOL - USE THIS WHEN PLAYER ASKS ABOUT QUESTS/MISSIONS**

    Retrieve all quests for a character. You MUST call this tool when a player asks about:
    - Their quests, quest log, active quests, or completed quests
    - Their missions, mission log, active missions, or mission status
    - Their tasks, task list, objectives, assignments, or jobs
    - Any variation like "what quests do I have?", "show my missions", "what tasks am I on?", "my objectives", etc.

    This tool retrieves the ACTUAL quests from the database. NEVER make up or invent quests - always use this tool to get the real quest data.

    Args:
        ctx: The context of the agent.
        request: The request to get the character's quests.

    Returns:
        ResponseQuests: The character's current quests as a list of quest dictionaries. If empty, the character has no active quests.
    """
    character = get_character_from_context(ctx, request)
    postgres_manager = ctx.deps.postgres_manager

    character_repository = CharacterRepository(postgres_manager)
    character = await character_repository.get_by_id(character.id)

    if not character:
        raise ValueError("Character not found")

    quest_repository = QuestRepository(postgres_manager)
    quests = await quest_repository.get_character_quests(character)

    # Convert quests to dictionaries for the response
    quest_dicts = [
        {
            "id": str(quest.id),
            "name": quest.name,
            "description": quest.description,
            "tasks": quest.tasks,
        }
        for quest in quests
    ]

    print(f"!!! Character quests: {[q['name'] for q in quest_dicts]}")

    return ResponseQuests(
        character=character,
        quests=quest_dicts,
    )


async def remove_character_quest(
    ctx: RunContext[GMAgentDependencies],
    request: RequestRemoveQuest,
) -> ResponseRemoveQuest:
    """
    Remove/abandon a quest from a character. Use this when a player wants to abandon, drop, cancel, or remove a quest.

    Players may use terms like:
    - "abandon quest", "drop quest", "cancel quest", "remove quest"
    - "abandon mission", "drop mission", "cancel mission"
    - "give up on [quest name]", "stop working on [quest name]"

    Args:
        ctx: The context of the agent.
        request: The request to remove the quest from the character.

    Returns:
        ResponseRemoveQuest: Confirmation that the quest was removed.
    """
    character = get_character_from_context(ctx, request)
    postgres_manager = ctx.deps.postgres_manager

    character_repository = CharacterRepository(postgres_manager)
    character = await character_repository.get_by_id(character.id)

    if not character:
        raise ValueError("Character not found")

    # Verify the character has this quest
    quest_repository = QuestRepository(postgres_manager)
    character_quests = await quest_repository.get_character_quests(character)

    quest_ids = [q.id for q in character_quests]
    if request.quest.id not in quest_ids:
        raise ValueError(f"Character does not have quest: {request.quest.name}")

    # Remove the quest and get items that need to be removed
    items_to_remove = await quest_repository.remove_character_quest(character, request.quest)

    # Remove quest items from inventory
    removed_items = []
    if items_to_remove:
        inventory = character.inventory if character.inventory else []
        updated_inventory = []

        for inv_item in inventory:
            item_removed = False
            for quest_item in items_to_remove:
                # Match by instance_id (preferred) or name
                if inv_item.get("instance_id") == quest_item.get("instance_id"):
                    # Remove this item completely
                    removed_items.append(
                        {
                            "name": inv_item.get("name"),
                            "quantity": inv_item.get("quantity", 0),
                        }
                    )
                    item_removed = True
                    break
                if inv_item.get("name") == quest_item.get("name"):
                    # Reduce quantity
                    current_qty = inv_item.get("quantity", 0)
                    remove_qty = quest_item.get("quantity", 0)
                    new_qty = current_qty - remove_qty

                    if new_qty > 0:
                        inv_item["quantity"] = new_qty
                        updated_inventory.append(inv_item)
                        removed_items.append(
                            {
                                "name": inv_item.get("name"),
                                "quantity": remove_qty,
                            }
                        )
                    else:
                        # Remove item completely
                        removed_items.append(
                            {
                                "name": inv_item.get("name"),
                                "quantity": current_qty,
                            }
                        )
                    item_removed = True
                    break

            if not item_removed:
                updated_inventory.append(inv_item)

        character.inventory = updated_inventory
        await character_repository.update(character)

        if removed_items:
            print(f"!!! Removed quest items: {removed_items}")

    print(f"!!! Removed quest: {request.quest.name} from character {character.name}")

    message = f"Quest '{request.quest.name}' has been abandoned."
    if removed_items:
        item_names = [item["name"] for item in removed_items]
        message += f" Quest items removed from inventory: {', '.join(item_names)}."

    return ResponseRemoveQuest(
        character=character,
        quest=request.quest,
        message=message,
    )

