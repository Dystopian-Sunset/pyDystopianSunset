"""
Message processor for handling game session messages and agent execution.

This module handles:
- Message classification (actionable vs player chat)
- Agent execution with context building
- Message history management
- Response filtering
"""

import json
import logging
import re
import time
import traceback
from datetime import UTC, datetime
from uuid import UUID

import discord
from pydantic_ai import Agent
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.messages import ModelMessagesTypeAdapter

from ds_common.metrics.service import get_metrics_service
from ds_common.models.character import Character
from ds_common.models.character_class import CharacterClass
from ds_common.models.game_master import GMAgentDependencies, GMHistory
from ds_common.models.game_session import GameSession
from ds_common.models.player import Player
from ds_common.repository.character import CharacterRepository
from ds_common.repository.game_session import GameSessionRepository
from ds_discord_bot.extensions.utils.messages import send_large_message
from ds_discord_bot.postgres_manager import PostgresManager

from .context_builder import ContextBuilder


class MessageProcessor:
    """
    Handles message processing for game sessions, including classification,
    agent execution, and history management.
    """

    def __init__(
        self,
        bot: discord.Client,
        postgres_manager: PostgresManager,
        agent: Agent,
        active_game_channels: dict,
    ):
        """
        Initialize the message processor.

        Args:
            bot: Discord bot instance (for accessing game_settings)
            postgres_manager: PostgreSQL manager for database operations
            agent: The pydantic_ai Agent instance for GM responses
            active_game_channels: Dictionary of active game channels (managed by Game class)
        """
        self.bot = bot
        self.postgres_manager = postgres_manager
        self.agent = agent
        self.active_game_channels = active_game_channels
        self.metrics = get_metrics_service()
        self.logger: logging.Logger = logging.getLogger(__name__)

    def _get_config(self):
        """Get configuration instance."""
        from ds_common.config_bot import get_config

        return get_config()

    def _create_redis_client(self, db_number: int):
        """
        Create a Redis client for the specified database number.

        Args:
            db_number: Redis database number (0 for prompt analyzer, 1 for memory)

        Returns:
            Redis client or None if Redis is not available
        """
        try:
            import redis.asyncio as redis

            config = self._get_config()
            redis_url = config.redis_url
            # Create connection with specific database number
            # Note: We don't await here as Redis connection is typically lazy
            return redis.from_url(redis_url, db=db_number)
        except Exception as e:
            self.logger.debug(f"Redis not available for db {db_number}: {e}")
            return None

    async def should_process_message(self, message: str) -> bool:
        """
        Determine if a message should be processed by the GM.

        Uses conversation classifier to determine if message is actionable
        (requires GM response) or player-to-player chat (should be skipped).

        Args:
            message: The player's message

        Returns:
            True if message should be processed by GM, False if it's player chat
        """
        try:
            from ds_discord_bot.extensions.conversation_classifier import (
                ConversationActionabilityClassifier,
            )

            # Initialize embedding service for classifier if available
            embedding_service = None
            try:
                from openai import AsyncOpenAI

                # Get embedding configuration
                config = self._get_config()
                embedding_base_url = config.ai_embedding_base_url
                embedding_api_key = config.ai_embedding_api_key

                # Initialize embedding service if base_url or api_key is provided
                if embedding_base_url or embedding_api_key:
                    # Build client kwargs - always include api_key (required by client library)
                    # Use dummy key for local services that don't require authentication
                    client_kwargs = {
                        "api_key": embedding_api_key
                        if embedding_api_key
                        else "sk-ollama-local-dummy-key-not-used"
                    }
                    if embedding_base_url:
                        client_kwargs["base_url"] = embedding_base_url

                    openai_client = AsyncOpenAI(**client_kwargs)
                    from ds_common.memory.embedding_service import EmbeddingService

                    # Try to get Redis client if available (for caching)
                    # Use database 0 for conversation classifier embeddings (same as prompt analyzer)
                    redis_client = self._create_redis_client(config.redis_db_prompt_analyzer)

                    # Get model and dimensions from config
                    embedding_model = config.ai_embedding_model
                    embedding_dimensions = config.ai_embedding_dimensions

                    embedding_service = EmbeddingService(
                        openai_client,
                        redis_client,
                        model=embedding_model,
                        dimensions=embedding_dimensions,
                    )
            except Exception as e:
                self.logger.debug(
                    f"Embedding service not available for conversation classification: {e}"
                )

            # Initialize classifier
            classifier = ConversationActionabilityClassifier(embedding_service=embedding_service)

            # Classify the message
            result = await classifier.classify(message)

            # If classified as player_chat with high confidence, skip processing
            if (
                result.category == "player_chat"
                and result.confidence >= classifier.config.skip_threshold
            ):
                self.logger.info(
                    f"Message classified as player_chat (confidence: {result.confidence:.2f}, "
                    f"method: {result.method}): {message[:50]}..."
                )
                return False

            # For actionable or ambiguous, process normally
            if result.category == "actionable":
                self.logger.debug(
                    f"Message classified as actionable (confidence: {result.confidence:.2f}, "
                    f"method: {result.method}): {message[:50]}..."
                )
            elif result.category == "ambiguous":
                self.logger.debug(
                    f"Message classified as ambiguous (confidence: {result.confidence:.2f}, "
                    f"method: {result.method}), processing anyway: {message[:50]}..."
                )

            return True
        except Exception as e:
            # If classifier fails, default to processing (fail-safe)
            self.logger.warning(f"Failed to classify message, defaulting to processing: {e}")
            return True

    def _detects_item_acquisition(self, message: str) -> bool:
        """
        Detect if the message indicates the player is acquiring items (salvage, find, collect, etc.).

        Args:
            message: The player's message

        Returns:
            True if item acquisition is detected
        """
        message_lower = message.lower()
        acquisition_keywords = [
            "salvage",
            "salvaging",
            "salvaged",
            "find",
            "finding",
            "found",
            "collect",
            "collecting",
            "collected",
            "grab",
            "grabbing",
            "grabbed",
            "take",
            "taking",
            "took",
            "pick up",
            "picking up",
            "picked up",
            "loot",
            "looting",
            "looted",
            "gather",
            "gathering",
            "gathered",
            "acquire",
            "acquiring",
            "acquired",
            "obtain",
            "obtaining",
            "obtained",
            "get",
            "getting",
            "got",
            "search for",
            "searching for",
            "searched for",
            "check for",
            "checking for",
            "checked for",
            "look for",
            "looking for",
            "looked for",
        ]
        return any(keyword in message_lower for keyword in acquisition_keywords)

    def _detects_item_usage(self, message: str) -> bool:
        """
        Detect if a player message likely involves using an item.

        Args:
            message: The player's message

        Returns:
            True if the message likely involves item usage
        """
        message_lower = message.lower()

        # Action verbs that typically require items
        action_keywords = [
            "use",
            "deploy",
            "activate",
            "detonate",
            "fire",
            "throw",
            "equip",
            "wield",
            "cast",
            "drink",
            "eat",
            "consume",
            "apply",
            "place",
            "set",
            "plant",
            "drop",
            "launch",
            "trigger",
            "press",
            "pull",
        ]

        # Item-related nouns
        item_keywords = [
            "bomb",
            "warhead",
            "weapon",
            "item",
            "tool",
            "device",
            "equipment",
            "gear",
            "grenade",
            "explosive",
            "ammo",
            "ammunition",
            "potion",
            "medkit",
            "cyberdeck",
            "implant",
            "mod",
            "upgrade",
        ]

        # Check for action verbs
        for keyword in action_keywords:
            if keyword in message_lower:
                return True

        # Check for item keywords
        for keyword in item_keywords:
            if keyword in message_lower:
                return True

        return False

    async def agent_run(
        self,
        game_session: GameSession,
        channel: discord.TextChannel,
        message: str,
        player: Player | None = None,
        character: Character | None = None,
        characters: dict[Character, CharacterClass] | None = None,
    ):
        game_session_repository = GameSessionRepository(self.postgres_manager)

        # If characters are not provided, get them all from the game session
        if not characters:
            characters = await game_session_repository.characters(game_session)

        # Analyze message to determine which prompt modules to load
        # Do this before any message preprocessing
        from ds_discord_bot.extensions.prompt_analyzer import PromptContextAnalyzer

        # Initialize embedding service for AI classification if available
        embedding_service = None
        try:
            from openai import AsyncOpenAI

            # Get embedding configuration
            config = self._get_config()
            embedding_base_url = config.ai_embedding_base_url
            embedding_api_key = config.ai_embedding_api_key

            # Initialize embedding service if base_url or api_key is provided
            if embedding_base_url or embedding_api_key:
                # Build client kwargs - always include api_key (required by client library)
                # Use dummy key for local services that don't require authentication
                client_kwargs = {
                    "api_key": embedding_api_key
                    if embedding_api_key
                    else "sk-ollama-local-dummy-key-not-used"
                }
                if embedding_base_url:
                    client_kwargs["base_url"] = embedding_base_url

                openai_client = AsyncOpenAI(**client_kwargs)
                from ds_common.memory.embedding_service import EmbeddingService

                # Try to get Redis client if available (for caching)
                # Use database 0 for prompt analyzer embeddings
                redis_client = self._create_redis_client(config.redis_db_prompt_analyzer)

                # Get model and dimensions from config
                embedding_model = config.ai_embedding_model
                embedding_dimensions = config.ai_embedding_dimensions

                embedding_service = EmbeddingService(
                    openai_client,
                    redis_client,
                    model=embedding_model,
                    dimensions=embedding_dimensions,
                )
        except Exception as e:
            self.logger.debug(f"Embedding service not available for prompt analysis: {e}")

        analyzer = PromptContextAnalyzer(self.postgres_manager, embedding_service=embedding_service)
        prompt_modules = await analyzer.analyze(message, character, game_session)

        agent_deps = GMAgentDependencies(
            postgres_manager=self.postgres_manager,
            game_session=game_session,
            player=player,
            action_character=character,
            characters=characters,
            prompt_modules=prompt_modules,
        )

        # Get game time context
        game_time_context = ""
        try:
            from ds_common.memory.game_time_service import GameTimeService

            game_time_service = GameTimeService(self.postgres_manager)
            game_time = await game_time_service.get_current_game_time()
            time_of_day = await game_time_service.get_time_of_day()
            month_name = await game_time_service.get_current_month_name()
            cycle_animal = await game_time_service.get_current_cycle_animal()

            month_display = f", Month: {month_name}" if month_name else ""
            cycle_display = f" ({cycle_animal} Year)" if cycle_animal else ""
            year_day = (
                game_time.year_day
                if hasattr(game_time, "year_day") and game_time.year_day
                else game_time.game_day
            )
            game_day = (
                game_time.game_day
                if hasattr(game_time, "game_day") and game_time.game_day
                else None
            )

            day_display = f"Day {game_day}" if game_day else f"Year Day {year_day}"
            game_time_context = (
                f"[GAME TIME: Year {game_time.game_year}{cycle_display}{month_display}, {day_display}, "
                f"Hour {game_time.game_hour:02d}:{game_time.game_minute:02d}, "
                f"Season: {game_time.season}, {time_of_day.title()}, "
                f"{'Daytime' if game_time.is_daytime else 'Nighttime'}]\n\n"
            )
        except Exception as e:
            # Don't fail if game time retrieval fails
            self.logger.warning(f"Failed to retrieve game time context: {e}")

        # Get active events context
        events_context = ""
        try:
            from ds_common.memory.calendar_service import CalendarService
            from ds_common.memory.game_time_service import GameTimeService
            from ds_common.repository.world_event import WorldEventRepository

            game_time_service = GameTimeService(self.postgres_manager)
            calendar_service = CalendarService(self.postgres_manager, game_time_service)

            # Get active world events
            world_event_repo = WorldEventRepository(self.postgres_manager)
            active_world_events = await world_event_repo.get_by_status("ACTIVE")

            # Filter by character location/region if available
            relevant_world_events = active_world_events
            if character and character.current_location:
                from ds_common.repository.location_node import LocationNodeRepository

                node_repo = LocationNodeRepository(self.postgres_manager)
                location_node = await node_repo.get_by_id(character.current_location)

                if location_node:
                    # Build list of location identifiers to match
                    location_identifiers = [location_node.location_name, str(location_node.id)]

                    # Add parent location if available
                    if location_node.parent_location_id:
                        parent_node = await node_repo.get_by_id(location_node.parent_location_id)
                        if parent_node:
                            location_identifiers.append(parent_node.location_name)
                            location_identifiers.append(str(parent_node.id))

                    # Filter events by regional scope
                    filtered_events = []
                    for event in active_world_events:
                        if not event.regional_scope:
                            # Events without regional scope are global, include them
                            filtered_events.append(event)
                        else:
                            # Check if character's location matches event's regional scope
                            scope_locations = event.regional_scope.get("locations", [])
                            if any(loc in location_identifiers for loc in scope_locations):
                                filtered_events.append(event)

                    relevant_world_events = filtered_events

            # Limit to 5 most relevant events
            relevant_world_events = relevant_world_events[:5]

            # Get active calendar events
            character_faction = None
            if character:
                # Try to get character's faction from their class or stats
                # For now, get all active events
                pass

            active_calendar_events = await calendar_service.get_active_events(
                region=None, faction=character_faction
            )

            # Format events context
            event_lines = []
            if relevant_world_events:
                world_event_names = [e.title for e in relevant_world_events[:3]]
                event_lines.append(f"Active World Events: {', '.join(world_event_names)}")

            if active_calendar_events:
                calendar_event_names = [e.name for e in active_calendar_events[:3]]
                event_lines.append(f"Active Calendar Events: {', '.join(calendar_event_names)}")

            if event_lines:
                events_context = f"[ACTIVE EVENTS: {' | '.join(event_lines)}]\n\n"
        except Exception as e:
            # Don't fail if events retrieval fails
            self.logger.warning(f"Failed to retrieve events context: {e}")

        # Retrieve compressed session memory context
        memory_context = ""
        try:
            from openai import AsyncOpenAI

            # Only retrieve if embedding service is available
            config = self._get_config()
            embedding_base_url = config.ai_embedding_base_url
            embedding_api_key = config.ai_embedding_api_key

            if embedding_base_url or embedding_api_key:
                from ds_common.memory.embedding_service import EmbeddingService
                from ds_common.memory.memory_compressor import MemoryCompressor
                from ds_common.memory.memory_retriever import MemoryRetriever
                from ds_common.repository.session_memory import SessionMemoryRepository

                # Build client kwargs - always include api_key (required by client library)
                # Use dummy key for local services that don't require authentication
                client_kwargs = {
                    "api_key": embedding_api_key
                    if embedding_api_key
                    else "sk-ollama-local-dummy-key-not-used"
                }
                if embedding_base_url:
                    client_kwargs["base_url"] = embedding_base_url

                openai_client = AsyncOpenAI(**client_kwargs)
                # Get model and dimensions from config
                embedding_model = config.ai_embedding_model
                embedding_dimensions = config.ai_embedding_dimensions

                # Try to get Redis client for memory embeddings (database 1)
                redis_client = self._create_redis_client(config.redis_db_memory)

                embedding_service = EmbeddingService(
                    openai_client,
                    redis_client,
                    model=embedding_model,
                    dimensions=embedding_dimensions,
                )
                memory_compressor = MemoryCompressor(self.postgres_manager, embedding_service)

                # Check how many memories exist for this session (for logging)
                session_memory_repo = SessionMemoryRepository(self.postgres_manager)
                all_memories = await session_memory_repo.get_by_session(
                    game_session.id, processed=False
                )
                self.logger.debug(
                    f"Found {len(all_memories)} unprocessed memories for session {game_session.id}"
                )

                # Get compressed session context with intelligent filtering
                # Use the player's message as query for semantic relevance
                # Use game_settings from bot (DB) instead of config
                game_settings = self.bot.game_settings
                session_context = await memory_compressor.get_compressed_session_context(
                    session_id=game_session.id,
                    query=message,  # Use message for semantic relevance
                    character_id=character.id if character else None,
                    max_memories=game_settings.memory_max_memories,
                    max_recent_memories=game_settings.memory_max_recent_memories,
                    importance_threshold=game_settings.memory_importance_threshold,
                )

                if session_context:
                    memory_context = session_context
                    # Log memory retrieval for verification
                    self.logger.info(
                        f"Retrieved compressed memory context for session {game_session.id}: "
                        f"{len(session_context)} chars (from {len(all_memories)} total memories)"
                    )
                else:
                    self.logger.debug(f"No memory context retrieved for session {game_session.id}")

                # Extract environmental items from recent GM responses
                environmental_items = await memory_compressor.extract_environmental_items(
                    session_id=game_session.id,
                    character_id=character.id if character else None,
                    lookback_minutes=game_settings.memory_environmental_items_lookback_minutes,
                )
                if environmental_items:
                    memory_context += environmental_items
                    self.logger.debug("Added environmental items context")

                # Also get compressed episode memories for character context
                if character:
                    memory_retriever = MemoryRetriever(self.postgres_manager, embedding_service)
                    episode_memories = await memory_retriever.get_character_memories(
                        character.id, limit=5
                    )

                    if episode_memories:
                        episode_context = await memory_compressor.compress_episode_summaries(
                            episode_memories, limit=3
                        )
                        if episode_context:
                            memory_context += episode_context
                            self.logger.debug(
                                f"Added {len(episode_memories)} episode memories to context"
                            )

                    # Get relevant world memories using semantic search
                    # Extract location_id if available from recent session memories
                    location_id = None
                    try:
                        if all_memories:
                            # Get the most recent memory with a location
                            for mem in sorted(
                                all_memories, key=lambda m: m.timestamp, reverse=True
                            ):
                                if mem.location_id:
                                    location_id = mem.location_id
                                    break
                    except Exception as e:
                        self.logger.debug(f"Failed to extract location_id: {e}")

                    # Get relevant world context using the player's message as query
                    try:
                        relevant_context = await memory_retriever.get_relevant_context(
                            query=message,
                            character_id=character.id,
                            location_id=location_id,
                            limit=5,  # Limit to top 5 most relevant world memories
                        )

                        # Format world memories into context string
                        world_memory_lines = []
                        if relevant_context.get("world_memories"):
                            for world_memory, distance in relevant_context["world_memories"][
                                :3
                            ]:  # Top 3 most relevant
                                # Calculate similarity score (1 - distance, where distance is cosine distance)
                                similarity = max(0.0, 1.0 - distance) if distance else 0.0

                                # Only include if similarity is above threshold (0.3)
                                if similarity >= 0.3:
                                    title = world_memory.title or "Untitled Memory"
                                    description = world_memory.description or ""
                                    # Truncate description if too long
                                    if len(description) > 200:
                                        description = description[:197] + "..."

                                    world_memory_lines.append(
                                        f"- {title}: {description} (relevance: {similarity:.2f})"
                                    )

                        if world_memory_lines:
                            world_context = (
                                "[WORLD LORE - Relevant History:\n"
                                + "\n".join(world_memory_lines)
                                + "\n]\n\n"
                            )
                            memory_context += world_context
                            self.logger.debug(
                                f"Added {len(world_memory_lines)} world memories to context"
                            )
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to retrieve world memory context: {e}", exc_info=True
                        )
            else:
                self.logger.debug("OpenAI API key not available, skipping memory retrieval")
        except Exception as e:
            # Don't fail if memory retrieval fails
            self.logger.warning(
                f"Failed to retrieve compressed session memory context: {e}", exc_info=True
            )

        # Get current character location for context (before message prepending)
        current_location_for_context = None
        current_location_node_for_context = None
        if character:
            try:
                character_repository = CharacterRepository(self.postgres_manager)
                fresh_character = await character_repository.get_by_id(character.id)
                if fresh_character and fresh_character.current_location:
                    from ds_common.repository.location_node import LocationNodeRepository

                    node_repository = LocationNodeRepository(self.postgres_manager)
                    current_location_node_for_context = await node_repository.get_by_id(
                        fresh_character.current_location
                    )
                    if current_location_node_for_context:
                        current_location_for_context = (
                            current_location_node_for_context.location_name
                        )
            except Exception as e:
                self.logger.debug(f"Failed to get character location for context: {e}")

        # Add validation context (location facts, travel routes, and graph data)
        validation_context = ""
        graph_context = ""
        if character and current_location_for_context:
            try:
                from ds_common.memory.location_graph_service import LocationGraphService
                from ds_common.memory.validators.geography_validator import (
                    GeographyValidator,
                )
                from ds_common.memory.validators.world_consistency_validator import (
                    WorldConsistencyValidator,
                )

                validator = WorldConsistencyValidator(self.postgres_manager)
                geo_validator = GeographyValidator(self.postgres_manager)
                graph_service = LocationGraphService(self.postgres_manager)

                # Get location facts
                facts = await validator.get_location_facts(current_location_for_context)
                if facts:
                    validation_context += f"\n[LOCATION FACTS for {current_location_for_context}: {', '.join(facts[:5])}]\n"

                # Get graph data (connected locations, available routes)
                if current_location_node_for_context:
                    # Location description and atmosphere for narrative context
                    if current_location_node_for_context.description:
                        graph_context += f"\n[LOCATION: {current_location_for_context} - {current_location_node_for_context.description[:200]}]\n"
                    if current_location_node_for_context.atmosphere:
                        sights = current_location_node_for_context.atmosphere.get("sights", [])
                        sounds = current_location_node_for_context.atmosphere.get("sounds", [])
                        smells = current_location_node_for_context.atmosphere.get("smells", [])
                        if sights or sounds or smells:
                            atmosphere_desc = []
                            if sights:
                                atmosphere_desc.append(f"Sights: {', '.join(sights[:3])}")
                            if sounds:
                                atmosphere_desc.append(f"Sounds: {', '.join(sounds[:3])}")
                            if smells:
                                atmosphere_desc.append(f"Smells: {', '.join(smells[:3])}")
                            graph_context += f"\n[ATMOSPHERE: {'; '.join(atmosphere_desc)}]\n"

                    connected_locations = await graph_service.get_connected_locations(
                        current_location_node_for_context.id, include_incoming=True
                    )
                    if connected_locations:
                        location_names = [loc.location_name for loc in connected_locations[:10]]
                        graph_context += f"\n[AVAILABLE ROUTES from {current_location_for_context}: {', '.join(location_names)}]\n"

                    # Get nearby POIs (child locations)
                    if current_location_node_for_context.location_type == "CITY":
                        from ds_common.repository.location_node import LocationNodeRepository

                        node_repo = LocationNodeRepository(self.postgres_manager)
                        nearby_pois = await node_repo.get_by_parent_location(
                            current_location_node_for_context.id
                        )
                        if nearby_pois:
                            poi_names = [poi.location_name for poi in nearby_pois[:15]]
                            graph_context += f"\n[NEARBY POIs in {current_location_for_context}: {', '.join(poi_names)}]\n"
                    elif current_location_node_for_context.location_type == "POI":
                        # If at a POI, show parent city and nearby POIs
                        if current_location_node_for_context.parent_location_id:
                            parent_node = await node_repository.get_by_id(
                                current_location_node_for_context.parent_location_id
                            )
                            if parent_node:
                                graph_context += (
                                    f"\n[PARENT LOCATION: {parent_node.location_name}]\n"
                                )

                            # Get sibling POIs (other POIs in same parent)
                            from ds_common.repository.location_node import LocationNodeRepository

                            node_repo = LocationNodeRepository(self.postgres_manager)
                            sibling_pois = await node_repo.get_by_parent_location(
                                current_location_node_for_context.parent_location_id
                            )
                            # Exclude current POI
                            sibling_pois = [
                                p
                                for p in sibling_pois
                                if p.id != current_location_node_for_context.id
                            ]
                            if sibling_pois:
                                poi_names = [poi.location_name for poi in sibling_pois[:10]]
                                graph_context += f"\n[NEARBY POIs: {', '.join(poi_names)}]\n"

                    # Get character associations
                    if current_location_node_for_context.character_associations:
                        associations = current_location_node_for_context.character_associations
                        npcs = associations.get("nearby_npcs", [])
                        if npcs:
                            npc_names = [npc.get("npc_name", "Unknown") for npc in npcs[:5]]
                            graph_context += f"\n[NPCs at {current_location_for_context}: {', '.join(npc_names)}]\n"

                # Get valid travel routes (for validation)
                direct_connections = await geo_validator.are_locations_connected(
                    current_location_for_context, "Agrihaven", allow_travel=False
                )
                travel_connections = await geo_validator.are_locations_connected(
                    current_location_for_context, "Agrihaven", allow_travel=True
                )
                if travel_connections and not direct_connections:
                    validation_context += f"\n[GEOGRAPHY: {current_location_for_context} requires proper travel to reach other cities. Instant methods (jump, teleport) are not valid.]\n"

            except Exception as e:
                self.logger.debug(f"Failed to add validation/graph context: {e}")

        if validation_context:
            memory_context += validation_context
        if graph_context:
            memory_context += graph_context

        # Pre-process message: If item usage is detected, prepend a reminder to check inventory
        if character and self._detects_item_usage(message):
            # Get current inventory to include in context
            character_repository = CharacterRepository(self.postgres_manager)
            fresh_character = await character_repository.get_by_id(character.id)
            if fresh_character:
                inventory = fresh_character.inventory if fresh_character.inventory else []
                if not inventory:
                    # If inventory is empty, add a system reminder
                    message = (
                        f"[SYSTEM REMINDER: Player inventory is EMPTY. They have no items. "
                        f"Any action requiring an item MUST be rejected. Check inventory with get_character_inventory tool if needed.]\n\n"
                        f"{message}"
                    )
                else:
                    # If inventory exists, remind to verify the specific item
                    message = (
                        f"[SYSTEM REMINDER: Player may be attempting to use an item. "
                        f"Current inventory: {inventory}. "
                        f"You MUST call get_character_inventory to verify they have the specific item before allowing the action.]\n\n"
                        f"{message}"
                    )

        # Pre-process message: If item acquisition is detected (salvage, find, collect), remind to add items
        if character and self._detects_item_acquisition(message):
            message = (
                f"[SYSTEM REMINDER: Player is attempting to acquire items (salvage, find, collect, etc.). "
                f"You MUST call `add_character_item` for EACH item they acquire. "
                f"If you describe multiple items (e.g., 'you salvage three items'), you MUST call `add_character_item` separately for each one. "
                f"NEVER describe items being acquired without actually adding them to inventory using the tool.]\n\n"
                f"{message}"
            )

        # Store original message before adding context (needed for memory capture)
        original_message = message

        # Combine all contexts: game time, events, memory
        combined_context = ""
        if game_time_context:
            combined_context += game_time_context
        if events_context:
            combined_context += events_context
        if memory_context:
            combined_context += memory_context

        # Prepend combined context to message
        if combined_context:
            message = combined_context + message
            self.logger.debug(f"Added {len(combined_context)} chars of context to message")

        # Get current character location from explicit field
        current_location = None
        current_location_node = None
        if character:
            try:
                # Get fresh character to ensure we have latest location
                character_repository = CharacterRepository(self.postgres_manager)
                fresh_character = await character_repository.get_by_id(character.id)
                if fresh_character and fresh_character.current_location:
                    from ds_common.repository.location_node import LocationNodeRepository

                    node_repository = LocationNodeRepository(self.postgres_manager)
                    current_location_node = await node_repository.get_by_id(
                        fresh_character.current_location
                    )
                    if current_location_node:
                        current_location = current_location_node.location_name
                        self.logger.debug(f"Character {character.name} is at: {current_location}")
            except Exception as e:
                self.logger.debug(f"Failed to get character location: {e}")

        # Validate player action before processing
        player_action_valid = True
        action_error = None
        if character and current_location:
            try:
                from ds_common.memory.validators.world_consistency_validator import (
                    WorldConsistencyValidator,
                )

                validator = WorldConsistencyValidator(self.postgres_manager)
                # Extract original message (before context prepending)
                original_message = message
                if combined_context:
                    # Remove context to get original player message
                    original_message = message.replace(combined_context, "", 1).strip()

                is_valid, error_msg = await validator.validate_action(
                    original_message, current_location
                )
                if not is_valid:
                    player_action_valid = False
                    action_error = error_msg
                    self.logger.warning(
                        f"Invalid player action detected: {original_message}. Error: {error_msg}"
                    )
            except Exception as e:
                self.logger.warning(f"Failed to validate player action: {e}", exc_info=True)

        agent_start_time = time.time()
        status = "success"
        try:
            response = await self.agent.run(
                message,
                message_history=self.active_game_channels[game_session.name]["history"],
                deps=agent_deps,
            )
        except Exception:
            status = "error"
            self.logger.error(f"Failed to run agent: {traceback.format_exc()}")
            await channel.send(
                "I'm sorry, but I was unable to process your request. Please try again later.",
                delete_after=10,
            )
            return
        finally:
            duration = time.time() - agent_start_time
            self.metrics.record_ai_agent_run("gm", duration, status)

        # Validate GM response
        response_text = response.output if hasattr(response, "output") and response.output else ""
        gm_response_valid = True
        response_error = None

        if character and current_location and response_text:
            try:
                from ds_common.memory.validators.world_consistency_validator import (
                    WorldConsistencyValidator,
                )

                validator = WorldConsistencyValidator(self.postgres_manager)
                # Check if response allows invalid actions
                is_valid, error_msg = await validator.validate_action(
                    response_text, current_location
                )
                if not is_valid:
                    gm_response_valid = False
                    response_error = error_msg
                    self.logger.warning(f"Invalid GM response detected. Error: {error_msg}")
            except Exception as e:
                self.logger.warning(f"Failed to validate GM response: {e}", exc_info=True)

        # If validation failed, send error message instead of GM response
        if not player_action_valid and action_error:
            error_message = (
                f"**Action Invalid:** {action_error}\n\n"
                f"Please try a different action that respects the world's geography and established facts."
            )
            await channel.send(error_message)
            # Still store history for tracking
            await self.store_history(
                game_session=game_session,
                player=player,
                characters=characters,
                message=message,
                response=response,
                original_message=original_message if "original_message" in locals() else None,
                action_character=character,
            )
            return
        if not gm_response_valid and response_error:
            # Log the violation but still send response (GM may have valid reason)
            self.logger.warning(
                f"GM response validation failed but sending anyway: {response_error}"
            )
            # Could optionally prepend a correction to the response
            # For now, just log it

        # Auto-detect and update character location if travel completed
        # Skip auto-detection if player's message was a path-finding request (open-ended statement)
        if character and response_text:
            try:
                import re

                message_lower = message.lower() if message else ""

                # Check if this was a path-finding request (open-ended statement)
                path_finding_patterns = [
                    r"find\s+(?:a\s+)?path\s+to",
                    r"how\s+do\s+i\s+get\s+to",
                    r"how\s+can\s+i\s+get\s+to",
                    r"i\s+need\s+to\s+get\s+to",
                    r"where\s+can\s+i\s+find",
                    r"i\s+want\s+to\s+find",
                    r"we\s+need\s+to\s+find",
                ]

                is_path_finding_request = any(
                    re.search(pattern, message_lower) for pattern in path_finding_patterns
                )

                # Only auto-detect location changes if this wasn't a path-finding request
                # Path-finding requests should offer options, not move the character
                if is_path_finding_request:
                    self.logger.debug(
                        f"Skipping auto-location update for path-finding request: {message[:50]}"
                    )
                else:
                    # Look for location mentions in response that indicate arrival
                    arrival_patterns = [
                        r"arrive(?:s|d)?\s+(?:at|in)\s+([A-Z][a-zA-Z\s]+?)(?:\s|$|,|\.)",
                        r"(?:step|walk|travel)(?:s|ed)?\s+(?:into|to|at)\s+([A-Z][a-zA-Z\s]+?)(?:\s|$|,|\.)",
                        r"find(?:s|ing)?\s+(?:yourself|themselves)\s+(?:at|in)\s+([A-Z][a-zA-Z\s]+?)(?:\s|$|,|\.)",
                        r"reach(?:es|ed)?\s+([A-Z][a-zA-Z\s]+?)(?:\s|$|,|\.)",
                    ]

                    new_location_name = None
                    for pattern in arrival_patterns:
                        matches = re.findall(pattern, response_text, re.IGNORECASE)
                        if matches:
                            potential_location = matches[-1].strip()
                            # Check if this is a known location
                            from ds_common.repository.location_node import LocationNodeRepository

                            node_repository = LocationNodeRepository(self.postgres_manager)
                            location_node = await node_repository.get_by_location_name(
                                potential_location, case_sensitive=False
                            )
                            if location_node:
                                new_location_name = location_node.location_name
                                break

                    # If we found a new location and character is not already there, update it
                    if new_location_name and new_location_name != current_location:
                        from ds_common.models.game_master import RequestUpdateCharacterLocation
                        from ds_common.repository.location_node import LocationNodeRepository

                        # Update character location directly using the tool to ensure memory is created
                        try:
                            # Use the update_character_location tool to ensure memory is properly tracked
                            request = RequestUpdateCharacterLocation(
                                character=character, location_name=new_location_name
                            )
                            # We can't call the tool directly here, so update manually and create memory
                            character_repository = CharacterRepository(self.postgres_manager)
                            fresh_character = await character_repository.get_by_id(character.id)
                            if fresh_character:
                                node_repository = LocationNodeRepository(self.postgres_manager)
                                location_node = await node_repository.get_by_location_name(
                                    new_location_name, case_sensitive=False
                                )
                                if location_node:
                                    old_location_id = fresh_character.current_location
                                    old_location_name = current_location

                                    fresh_character.current_location = location_node.id
                                    await character_repository.update(fresh_character)

                                    # Create memory event for auto-detected location change
                                    try:
                                        from openai import AsyncOpenAI

                                        from ds_common.memory.memory_processor import (
                                            MemoryProcessor,
                                        )

                                        config = self._get_config()
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

                                            redis_client = self._create_redis_client(
                                                config.redis_db_memory
                                            )

                                            memory_processor = MemoryProcessor(
                                                self.postgres_manager,
                                                openai_client,
                                                redis_client=redis_client,
                                                embedding_model=embedding_model,
                                                embedding_dimensions=embedding_dimensions,
                                            )

                                            travel_description = f"Auto-detected travel from {old_location_name or 'unknown location'} to {new_location_name}"
                                            content = {
                                                "action": "location_change",
                                                "description": travel_description,
                                                "from_location": old_location_name,
                                                "to_location": new_location_name,
                                                "response": response_text[:200]
                                                if response_text
                                                else "",
                                                "auto_detected": True,
                                            }

                                            await memory_processor.capture_session_event(
                                                session_id=game_session.id,
                                                character_id=fresh_character.id,
                                                memory_type="action",
                                                content=content,
                                                participants=None,
                                                location_id=location_node.id,
                                            )
                                            self.logger.info(
                                                f"Created memory event for auto-detected location change: {old_location_name} -> {new_location_name}"
                                            )
                                    except Exception as e:
                                        self.logger.warning(
                                            f"Failed to create memory event for auto-detected location change: {e}",
                                            exc_info=True,
                                        )

                                    self.logger.info(
                                        f"Auto-updated {character.name} location from {old_location_name} to {new_location_name}"
                                    )
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to auto-update character location: {e}", exc_info=True
                            )
            except Exception as e:
                self.logger.debug(f"Failed to auto-update character location: {e}")

        await self.store_history(
            game_session=game_session,
            player=player,
            characters=characters,
            message=message,
            response=response,
            action_character=character,
            original_message=original_message if "original_message" in locals() else None,
        )

        # Filter out reasoning/thinking content before sending
        filtered_response = self._filter_reasoning_content(response_text)

        # Log if content was filtered (for debugging)
        if filtered_response != response_text:
            original_length = len(response_text)
            filtered_length = len(filtered_response)
            if original_length > filtered_length:
                self.logger.debug(
                    f"Filtered {original_length - filtered_length} characters of reasoning/internal content from GM response"
                )

        async for chunk in send_large_message(filtered_response):
            await channel.send(chunk)

    def _filter_reasoning_content(self, text: str) -> str:
        """
        Filter out reasoning, thinking, or internal process content from GM responses.

        Removes patterns like:
        - "I need to...", "Let me...", "I should..."
        - "We need to update...", "Let's call..."
        - XML-like tags: <reasoning>, <think>, etc.
        - Tool call references that leaked into output
        - JSON structures
        - Function names and system operations

        Args:
            text: The raw GM response text

        Returns:
            Filtered text with reasoning content removed
        """
        import re

        if not text:
            return text

        # Remove {Prompt: ...} patterns that the agent may include literally
        # This matches {Prompt: ...} at the end of the text or anywhere
        text = re.sub(r"\s*\{Prompt:[^}]*\}\s*$", "", text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r"\s*\{Prompt:[^}]*\}\s*", " ", text, flags=re.IGNORECASE)

        # Aggressively remove reasoning blocks that appear before narrative
        # Look for patterns like "Let's output narrative: ... But we don't have... It's fine. Just narrate. Then prompt."
        # and remove everything up to the first actual narrative sentence
        # Narrative typically starts with: "The", "You", "Basi", "Your", "He", "She", "They", "It", "A", "An", or descriptive text
        reasoning_intro_patterns = [
            r"^let\'?s output[^.!?]*[.!?]\s*",
            r"^let\'?s craft[^.!?]*[.!?]\s*",
            r"^but we don\'?t have[^.!?]*[.!?]\s*",
            r"^it\'?s fine[^.!?]*[.!?]\s*",
            r"^just narrate[^.!?]*[.!?]\s*",
            r"^then prompt[^.!?]*[.!?]\s*",
        ]

        # Find the first line that looks like actual narrative (starts with common narrative words)
        lines = text.split("\n")
        narrative_start_idx = -1
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            # Check if this line starts with narrative (not reasoning)
            if re.match(
                r"^(the|you|your|basi|he|she|they|it|a|an|this|that|as|when|where|while|through|between|beneath|above|below|kneel|slip|dim|neon|flicker|glow|hum|echo)",
                line_stripped,
                re.IGNORECASE,
            ):
                narrative_start_idx = i
                break

        # If we found narrative, remove everything before it that looks like reasoning
        if narrative_start_idx > 0:
            # Check if the lines before narrative_start_idx are reasoning
            reasoning_lines = []
            for i in range(narrative_start_idx):
                line = lines[i].strip()
                if line and any(
                    re.search(pattern, line, re.IGNORECASE) for pattern in reasoning_intro_patterns
                ):
                    reasoning_lines.append(i)
                # Also check for common reasoning phrases
                line_lower = line.lower()
                if any(
                    phrase in line_lower
                    for phrase in [
                        "let's output",
                        "let's craft",
                        "but we don't",
                        "it's fine",
                        "just narrate",
                        "then prompt",
                        "we could just",
                        "could find",
                        "maybe a",
                        "not modify",
                        "no rule for",
                    ]
                ):
                    reasoning_lines.append(i)

            # Remove reasoning lines
            if reasoning_lines:
                # Remove from the end backwards to preserve indices
                for i in reversed(reasoning_lines):
                    lines.pop(i)
                text = "\n".join(lines)

        # Remove reasoning patterns that appear at the start of text (before any narrative)
        # These are often directives to the AI itself, appearing as a block of short sentences
        # Match a block of reasoning directives at the start (e.g., "We must describe... No tool call... End prompt.")
        reasoning_block_pattern = r"^(?:(?:we must|must describe|we need to|i need to|i must|i should|no tool call|tool call visible|mention new time|end prompt|use description|likely less|likely more|let\'?s output|let\'?s craft|let\'?s call|but we don\'?t|we don\'?t have|it\'?s fine|just narrate|then prompt|we could just say|could find|maybe a|not modify|no rule for)[^.!?]*[.!?]\s*)+"
        text = re.sub(reasoning_block_pattern, "", text, flags=re.IGNORECASE | re.MULTILINE)

        # Remove common reasoning prefixes that appear before narrative
        reasoning_prefixes = [
            r"^let\'?s output[^.!?]*[.!?]\s*",
            r"^let\'?s craft[^.!?]*[.!?]\s*",
            r"^but we don\'?t have[^.!?]*[.!?]\s*",
            r"^it\'?s fine[^.!?]*[.!?]\s*",
            r"^just narrate[^.!?]*[.!?]\s*",
            r"^then prompt[^.!?]*[.!?]\s*",
            r"^we could just say[^.!?]*[.!?]\s*",
            r"^could find[^.!?]*[.!?]\s*",
            r"^maybe a[^.!?]*[.!?]\s*",
            r"^not modify[^.!?]*[.!?]\s*",
            r"^no rule for[^.!?]*[.!?]\s*",
        ]
        for pattern in reasoning_prefixes:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.MULTILINE)

        # Remove reasoning blocks that appear mid-text (e.g., "Let's output narrative: ... But we don't have...")
        # This catches multi-sentence reasoning blocks anywhere in the text
        reasoning_mid_block = r"(?:let\'?s output|let\'?s craft|but we don\'?t|we don\'?t have|it\'?s fine|just narrate|then prompt|we could just say)[^.!?]*[.!?]\s*(?:[^.!?]*[.!?]\s*){0,3}(?=the dim|you |basi |the neon|your |he |she |they |it )"
        text = re.sub(reasoning_mid_block, "", text, flags=re.IGNORECASE | re.DOTALL)

        # Also remove individual reasoning sentences anywhere in the text
        reasoning_sentence_patterns = [
            r"[^.!?]*(?:we must|must describe|no tool call|tool call visible|mention new time|end prompt|use description|let\'?s output|let\'?s craft|let\'?s call|but we don\'?t|we don\'?t have|it\'?s fine|just narrate|then prompt|we could just say|could find)[^.!?]*[.!?]",
        ]
        for pattern in reasoning_sentence_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Remove XML-like reasoning tags and their content (including unclosed tags)
        text = re.sub(r"<reasoning>.*?</reasoning>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<thought>.*?</thought>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<reasoning>.*", "", text, flags=re.DOTALL | re.IGNORECASE)  # Unclosed tags
        text = re.sub(r"<think>.*", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<thought>.*", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<think>.*", "", text, flags=re.DOTALL | re.IGNORECASE)

        # Remove entire JSON blocks (tool call outputs)
        text = re.sub(
            r'\{[^{}]*"(location_id|character_id|quest_id|item|quest|character|location)":\s*"[^"]*"[^}]*\}',
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r'\{[^{}]*"(location_id|character_id|quest_id|item|quest|character|location)":\s*[^,}]+[^}]*\}',
            "",
            text,
            flags=re.IGNORECASE,
        )

        # Remove lines that contain reasoning patterns or system operations
        lines = text.split("\n")
        filtered_lines = []

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                filtered_lines.append(line)
                continue

            line_lower = line_stripped.lower()

            # Skip lines that are clearly reasoning/internal process
            reasoning_patterns = [
                "we need to",
                "let's call",
                "let's update",
                "let's output",
                "let's craft",
                "let's say",
                "let me call",
                "let me update",
                "i need to",
                "i should",
                "i will call",
                "i will update",
                "calling tool",
                "calling function",
                "tool:",
                "function:",
                "updating character",
                "updating location",
                "getting character",
                "getting location",
                "checking character",
                "checking location",
                "fetching",
                "retrieving",
                "querying",
                "but we don't",
                "we don't have",
                "it's fine",
                "just narrate",
                "then prompt",
                "could find",
                "maybe a",
                "we could just",
                "not modify",
                "no rule for",
                "executing",
                "running tool",
                "invoking",
                "we must",
                "must describe",
                "no tool call",
                "tool call visible",
                "mention new time",
                "end prompt",
                "use description",
                "likely less",
                "likely more",
            ]

            if any(pattern in line_lower for pattern in reasoning_patterns):
                continue

            # Skip lines that look like tool calls or function calls (with or without parentheses)
            if re.search(
                r"\b(update_|get_|add_|remove_|create_|find_|check_|start_|end_|set_|modify_|delete_|fetch_|retrieve_|query_|execute_|invoke_)\w*\s*\(",
                line,
                re.IGNORECASE,
            ):
                continue

            # Skip lines that are just function names
            if re.match(
                r"^\s*(update_|get_|add_|remove_|create_|find_|check_|start_|end_|set_|modify_|delete_|fetch_|retrieve_|query_|execute_|invoke_)\w+\s*$",
                line,
                re.IGNORECASE,
            ):
                continue

            # Skip lines that look like JSON (even partial)
            if re.match(
                r'^\s*\{.*"(location_id|character_id|quest_id|item|quest|character|location|name|description|id)":',
                line,
                re.IGNORECASE,
            ):
                continue

            # Skip lines that are just curly braces or JSON-like structures
            if re.match(r"^\s*[\{\[].*[\}\]]\s*$", line) and ('"' in line or ":" in line):
                # Check if it looks like JSON (has quotes and colons)
                if re.search(r'"[^"]*"\s*:', line):
                    continue

            # Skip lines that mention specific tool names
            tool_names = [
                "update_character_location",
                "get_character_inventory",
                "add_character_item",
                "remove_character_item",
                "add_character_quest",
                "remove_character_quest",
                "get_character_quests",
                "update_character",
                "get_character",
                "create_quest",
                "find_location",
            ]

            if any(tool_name in line_lower for tool_name in tool_names):
                continue

            # Keep the line if it passed all filters
            filtered_lines.append(line)

        filtered_text = "\n".join(filtered_lines)

        # Remove standalone JSON objects that might have been missed
        filtered_text = re.sub(
            r'\n\s*\{[^{}]*"(location_id|character_id|quest_id|item|quest|character|location)":\s*"[^"]*"[^}]*\}\s*\n',
            "\n",
            filtered_text,
            flags=re.IGNORECASE,
        )

        # Clean up multiple consecutive newlines
        filtered_text = re.sub(r"\n{3,}", "\n\n", filtered_text)

        # Remove leading/trailing whitespace but preserve structure
        return filtered_text.strip()

    async def store_history(
        self,
        game_session: GameSession,
        player: Player,
        characters: list[Character],
        message: str,
        response: AgentRunResult,
        action_character: Character | None = None,
        original_message: str | None = None,
    ) -> None:
        messages = json.loads(response.new_messages_json())

        self.logger.debug(f"Storing history for game session {game_session.id}: {messages}")

        # Verify the game session still exists in the database before storing history
        game_session_repository = GameSessionRepository(self.postgres_manager)
        try:
            existing_session = await game_session_repository.get_by_id(game_session.id)
            if not existing_session:
                self.logger.warning(
                    f"Cannot store history: Game session {game_session.id} ({game_session.name}) "
                    f"no longer exists in database. Session may have been deleted."
                )
                return
        except Exception as e:
            self.logger.warning(
                f"Failed to verify game session existence before storing history: {e}"
            )
            # Continue anyway - the create will fail if session doesn't exist

        gm_history = GMHistory(
            game_session_id=game_session.id,
            player_id=player.id if player else None,
            action_character=action_character.name if action_character else None,
            characters=[character.name for character, _ in characters],
            request=message,
            model_messages=messages,
            created_at=datetime.now(UTC),
        )
        try:
            from ds_common.models.game_master import GMHistory as GMHistoryModel
            from ds_common.repository.base_repository import BaseRepository
            from sqlalchemy.exc import IntegrityError

            gm_history_repo = BaseRepository(self.postgres_manager, GMHistoryModel)
            gm_history = await gm_history_repo.create(gm_history)
        except IntegrityError as e:
            # Handle foreign key violations specifically
            if "foreign key constraint" in str(e).lower() or "game_session_id" in str(e):
                self.logger.warning(
                    f"Cannot store GM history: Game session {game_session.id} ({game_session.name}) "
                    f"no longer exists in database. This may occur if the session was deleted "
                    f"while history was being stored."
                )
            else:
                self.logger.error(f"Database integrity error storing GM history: {e}")
        except Exception as e:
            self.logger.error(f"Failed to store long term history: {e}", exc_info=True)

        # Capture session event for memory system
        try:
            from openai import AsyncOpenAI

            # Only capture if embedding service is available
            config = self._get_config()
            embedding_base_url = config.ai_embedding_base_url
            embedding_api_key = config.ai_embedding_api_key

            if embedding_base_url or embedding_api_key:
                from ds_common.memory.memory_processor import MemoryProcessor

                # Build client kwargs - always include api_key (required by client library)
                # Use dummy key for local services that don't require authentication
                client_kwargs = {
                    "api_key": embedding_api_key
                    if embedding_api_key
                    else "sk-ollama-local-dummy-key-not-used"
                }
                if embedding_base_url:
                    client_kwargs["base_url"] = embedding_base_url

                openai_client = AsyncOpenAI(**client_kwargs)
                # Get model and dimensions from config
                embedding_model = config.ai_embedding_model
                embedding_dimensions = config.ai_embedding_dimensions

                # Try to get Redis client for memory embeddings (database 1)
                redis_client = self._create_redis_client(config.redis_db_memory)

                memory_processor = MemoryProcessor(
                    self.postgres_manager,
                    openai_client,
                    redis_client=redis_client,
                    embedding_model=embedding_model,
                    embedding_dimensions=embedding_dimensions,
                )

                if action_character:
                    # Extract event details from message and response
                    # Use original_message parameter if provided (without game time context), otherwise fall back to message
                    action_text = original_message if original_message else message
                    response_text = (
                        response.output if hasattr(response, "output") and response.output else ""
                    )
                    content = {
                        "action": action_text[
                            :100
                        ],  # Use original message without game time context
                        "description": str(messages[-1].get("content", ""))[:500]
                        if messages
                        else "",
                        "response": response_text[:500],
                    }

                    participant_ids = [
                        char.id for char, _ in characters if char.id != action_character.id
                    ]

                    # Use character's current location from location_node with full context
                    location_id = None
                    location_string = None
                    location_context = None
                    try:
                        # Get character's current location from location_node
                        character_repository = CharacterRepository(self.postgres_manager)
                        fresh_character = await character_repository.get_by_id(action_character.id)
                        if fresh_character and fresh_character.current_location:
                            location_id = fresh_character.current_location

                            # Get full location context including parent locations
                            context_builder = ContextBuilder(self.postgres_manager)
                            location_context = await context_builder.get_location_context(location_id)
                            location_string = location_context.get("location_name")

                            # Enhance content with location context
                            # Store both location_id (for canonical locations) and location_name (for narrative locations)
                            # Also persist location details (description, atmosphere) for important memories
                            if location_context:
                                location_info = {
                                    "current_location": location_string,
                                    "location_type": location_context.get("location_type"),
                                    "location_id": str(
                                        location_id
                                    ),  # Store as string for JSON compatibility
                                }
                                if location_context.get("parent_location_name"):
                                    location_info["parent_location"] = location_context.get(
                                        "parent_location_name"
                                    )
                                if location_context.get("city"):
                                    location_info["city"] = location_context.get("city")
                                if location_context.get("district"):
                                    location_info["district"] = location_context.get("district")
                                if location_context.get("sector"):
                                    location_info["sector"] = location_context.get("sector")
                                if location_context.get("region_name"):
                                    location_info["region"] = location_context.get("region_name")

                                # Build location searchable text for semantic matching
                                # This helps find memories even when location isn't canonical
                                location_parts = [location_string]
                                if location_context.get("parent_location_name"):
                                    location_parts.append(
                                        location_context.get("parent_location_name")
                                    )
                                if location_context.get("city"):
                                    location_parts.append(location_context.get("city"))
                                location_info["location_searchable"] = " ".join(location_parts)

                                # Get location details from location_node for persistence
                                # Store description and atmosphere for important memories
                                try:
                                    from ds_common.repository.location_node import (
                                        LocationNodeRepository,
                                    )

                                    node_repo = LocationNodeRepository(self.postgres_manager)
                                    location_node = await node_repo.get_by_id(location_id)
                                    if location_node:
                                        # Store description (truncated for memory efficiency)
                                        if location_node.description:
                                            location_info["description"] = (
                                                location_node.description[:500]
                                            )

                                        # Store atmosphere (sensory details)
                                        if location_node.atmosphere:
                                            location_info["atmosphere"] = location_node.atmosphere

                                        # Store theme if available
                                        if location_node.theme:
                                            location_info["theme"] = location_node.theme

                                        # Store physical properties if available
                                        if location_node.physical_properties:
                                            location_info["physical_properties"] = (
                                                location_node.physical_properties
                                            )

                                        # Store character associations if available (NPCs, factions)
                                        if location_node.character_associations:
                                            location_info["character_associations"] = (
                                                location_node.character_associations
                                            )
                                except Exception as e:
                                    self.logger.debug(
                                        f"Failed to get location details for memory: {e}"
                                    )

                                content["location_context"] = location_info
                            else:
                                # Even without full context, store location name for semantic search
                                if location_string:
                                    content["location_context"] = {
                                        "current_location": location_string,
                                        "location_id": str(location_id) if location_id else None,
                                        "location_searchable": location_string,
                                    }

                            self.logger.debug(
                                f"Capturing memory with location: {location_string} (ID: {location_id}), "
                                f"parent: {location_context.get('parent_location_name') if location_context else None}, "
                                f"city: {location_context.get('city') if location_context else None}"
                            )
                    except Exception as e:
                        self.logger.debug(f"Failed to get character location for memory: {e}")

                    await memory_processor.capture_session_event(
                        session_id=game_session.id,
                        character_id=action_character.id,
                        memory_type="action",
                        content=content,
                        participants=participant_ids,
                        location_id=location_id,
                    )
        except Exception as e:
            # Don't fail if memory capture fails
            self.logger.warning(f"Failed to capture session event: {e}")

        # Filter reasoning content from messages before storing in history to prevent contamination
        filtered_messages = []
        for msg in messages:
            if isinstance(msg, dict) and "content" in msg:
                filtered_content = self._filter_reasoning_content(str(msg["content"]))
                # Only keep message if it has content after filtering
                if filtered_content.strip():
                    filtered_msg = msg.copy()
                    filtered_msg["content"] = filtered_content
                    filtered_messages.append(filtered_msg)
            else:
                # Keep non-content messages as-is
                filtered_messages.append(msg)

        # Only store in active_game_channels if the session is still active
        # This prevents KeyError if the session was ended/deleted while history was being stored
        if game_session.name in self.active_game_channels:
            self.active_game_channels[game_session.name]["history"].extend(filtered_messages)

            # We only keep the last 20 messages in memory
            self.active_game_channels[game_session.name]["history"] = self.active_game_channels[
                game_session.name
            ]["history"][-20:]
        else:
            self.logger.debug(
                f"Game session {game_session.name} not in active_game_channels, "
                f"skipping in-memory history storage. Session may have been ended."
            )

    async def load_history(self, game_session: GameSession) -> list[ModelMessagesTypeAdapter]:
        """
        Load message history for a game session from the database.

        Args:
            game_session: The game session to load history for

        Returns:
            List of message history entries
        """
        # If the game session is not found, return an empty list as there is no history to load
        if not game_session:
            return []

        self.logger.debug(f"Loading history for game session {game_session.name}")
        from sqlmodel import select

        from ds_common.models.game_master import GMHistory as GMHistoryModel

        async with self.postgres_manager.get_session() as sess:
            stmt = (
                select(GMHistoryModel)
                .where(GMHistoryModel.game_session_id == game_session.id)
                .order_by(GMHistoryModel.created_at.desc())
                .limit(20)
            )
            result = await sess.execute(stmt)
            gm_histories = list(result.scalars().all())

        if not gm_histories:
            return []

        history = []
        for gm_history_model in gm_histories:
            try:
                history.extend(
                    ModelMessagesTypeAdapter.validate_python(gm_history_model.model_messages)
                )
            except Exception:
                self.logger.error(f"Failed to load history: {traceback.format_exc()}")
                continue

        return history
