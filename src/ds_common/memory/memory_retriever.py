"""Memory retriever for semantic search and context retrieval."""

import logging
import time
from uuid import UUID

from ds_common.memory.embedding_service import EmbeddingService
from ds_common.metrics.service import get_metrics_service
from ds_common.repository.episode_memory import EpisodeMemoryRepository
from ds_common.repository.world_memory import WorldMemoryRepository
from ds_discord_bot.postgres_manager import PostgresManager


class MemoryRetriever:
    """Service for retrieving relevant memories for context."""

    def __init__(
        self,
        postgres_manager: PostgresManager,
        embedding_service: EmbeddingService,
    ):
        """
        Initialize the memory retriever.

        Args:
            postgres_manager: PostgreSQL manager
            embedding_service: Embedding service for generating query embeddings
        """
        self.logger = logging.getLogger(__name__)
        self.postgres_manager = postgres_manager
        self.embedding_service = embedding_service
        self.metrics = get_metrics_service()

        # Initialize repositories
        self.episode_repo = EpisodeMemoryRepository(postgres_manager)
        self.world_repo = WorldMemoryRepository(postgres_manager)

    async def get_relevant_context(
        self,
        query: str,
        character_id: UUID | None = None,
        location_id: UUID | None = None,
        limit: int = 10,
    ) -> dict:
        """
        Get relevant context for a query using semantic search.

        Args:
            query: Query text
            character_id: Optional character ID to filter by
            location_id: Optional location ID to filter by
            limit: Maximum number of results

        Returns:
            Dictionary with relevant memories and context
        """
        self.logger.debug(f"Getting relevant context for query: {query[:50]}...")

        start_time = time.time()

        # Generate query embedding
        query_embedding = await self.embedding_service.generate(query)

        # Search world memories (pass dimensions from embedding service)
        world_results = await self.world_repo.semantic_search(
            query_embedding,
            limit=limit * 2,  # Get more results to filter by location
            is_public=True,
            dimensions=self.embedding_service.dimensions,
        )

        # Filter by location if provided
        #
        # LOCATION TRACKING STRATEGY:
        # - Canonical locations: Have location_nodes with UUIDs, stored in related_entities.locations
        # - Narrative locations: Mentioned in text but may not have location_nodes
        #   - Stored in memory content as location_context with location_searchable text
        #   - Found via semantic search on narrative text
        # - Hybrid approach: Use UUID matching first, fall back to semantic matching
        #   This ensures we find memories even when locations aren't fully canonical
        #   (e.g., "Maintenance Bay 7" mentioned in narrative but not yet a location_node)
        #
        if location_id:
            # First, try to get location name for semantic matching
            location_name = None
            location_searchable = None
            try:
                from ds_common.repository.location_node import LocationNodeRepository

                node_repo = LocationNodeRepository(self.postgres_manager)
                location_node = await node_repo.get_by_id(location_id)
                if location_node:
                    location_name = location_node.location_name
                    # Build searchable location text (location + parent + city)
                    location_parts = [location_name]
                    if location_node.parent_location_id:
                        parent_node = await node_repo.get_by_id(location_node.parent_location_id)
                        if parent_node:
                            location_parts.append(parent_node.location_name)
                    location_searchable = " ".join(location_parts)
            except Exception as e:
                self.logger.debug(f"Failed to get location name for semantic matching: {e}")

            filtered_world_results = []
            location_id_str = str(location_id)

            for wm, distance in world_results:
                matched = False

                # Method 1: Check if location_id is in related_entities (canonical location match)
                if wm.related_entities:
                    locations = wm.related_entities.get("locations", [])
                    location_ids = [
                        str(loc) if not isinstance(loc, str) else loc for loc in locations
                    ]
                    if location_id_str in location_ids:
                        filtered_world_results.append((wm, distance))
                        matched = True

                # Method 2: Check regional_context for location references
                if not matched and wm.regional_context:
                    # Regional context might have location references
                    # This is a fallback check
                    pass

                # Method 3: Semantic matching on location names in narrative (for non-canonical locations)
                # If we have location name, use semantic search on full narrative text
                if not matched and location_searchable:
                    # The embedding already includes location context from the narrative
                    # Lower distance means more similar, so we accept results within a threshold
                    # For location-specific matching, we want distance < 0.3 (higher similarity)
                    if distance < 0.3:
                        # Check if location name appears in narrative text
                        narrative_text = f"{wm.title or ''} {wm.description or ''} {wm.full_narrative or ''}".lower()
                        if (location_name and location_name.lower() in narrative_text) or (
                            location_searchable
                            and any(
                                part.lower() in narrative_text
                                for part in location_searchable.split()
                                if len(part) > 3  # Skip short words
                            )
                        ):
                            filtered_world_results.append((wm, distance))
                            matched = True

            # If we have filtered results, use them; otherwise use all results (semantic search already filtered)
            if filtered_world_results:
                # Sort by distance (lower is better) and limit
                filtered_world_results.sort(key=lambda x: x[1])
                world_results = filtered_world_results[:limit]
            else:
                # No location matches, but still return top results (semantic search already filtered by relevance)
                world_results = world_results[:limit]
        else:
            # No location filter, just limit results
            world_results = world_results[:limit]

        # Get episode memories if character is provided
        episode_memories = []
        if character_id:
            # Filter episode memories by character and optionally by location
            # get_by_characters expects a list and doesn't accept limit parameter
            episode_results = await self.episode_repo.get_by_characters([character_id])

            # Filter by location if provided
            # Use both UUID matching (for canonical locations) and semantic matching (for narrative locations)
            if location_id:
                # Get location name for semantic matching
                location_name = None
                location_searchable = None
                try:
                    from ds_common.repository.location_node import LocationNodeRepository

                    node_repo = LocationNodeRepository(self.postgres_manager)
                    location_node = await node_repo.get_by_id(location_id)
                    if location_node:
                        location_name = location_node.location_name
                        # Build searchable location text
                        location_parts = [location_name]
                        if location_node.parent_location_id:
                            parent_node = await node_repo.get_by_id(
                                location_node.parent_location_id
                            )
                            if parent_node:
                                location_parts.append(parent_node.location_name)
                        location_searchable = " ".join(location_parts)
                except Exception as e:
                    self.logger.debug(f"Failed to get location name for episode filtering: {e}")

                filtered_episodes = []
                location_id_str = str(location_id)

                for ep in episode_results:
                    matched = False

                    # Method 1: Check if location_id is in episode's locations (canonical location match)
                    if ep.locations:
                        location_ids = [
                            str(loc) if not isinstance(loc, str) else loc for loc in ep.locations
                        ]
                        if location_id_str in location_ids:
                            filtered_episodes.append(ep)
                            matched = True

                    # Method 2: Semantic matching on episode summary/narrative (for non-canonical locations)
                    # Check if location name appears in episode text
                    if not matched and location_searchable:
                        episode_text = f"{ep.title or ''} {ep.summary or ''} {ep.one_sentence_summary or ''}".lower()
                        if (location_name and location_name.lower() in episode_text) or (
                            location_searchable
                            and any(
                                part.lower() in episode_text
                                for part in location_searchable.split()
                                if len(part) > 3  # Skip short words
                            )
                        ):
                            filtered_episodes.append(ep)
                            matched = True

                episode_memories = filtered_episodes[:limit]
            else:
                episode_memories = episode_results[:limit]

        # Track metrics
        duration = time.time() - start_time
        self.metrics.record_memory_retrieval()
        self.metrics.record_memory_operation("retrieval", duration)

        return {
            "world_memories": [(wm, distance) for wm, distance in world_results],
            "episode_memories": episode_memories,
            "query": query,
        }

    async def get_character_memories(
        self,
        character_id: UUID,
        limit: int = 20,
    ) -> list:
        """
        Get memories involving a specific character.

        Args:
            character_id: Character ID
            limit: Maximum number of results

        Returns:
            List of episode memories
        """
        self.logger.debug(f"Getting memories for character {character_id}")

        episodes = await self.episode_repo.get_by_characters([character_id])
        return episodes[:limit]

    async def get_location_lore(
        self,
        location_id: UUID,
        limit: int = 10,
    ) -> list:
        """
        Get world memories related to a specific location.

        Args:
            location_id: Location ID
            limit: Maximum number of results

        Returns:
            List of world memories
        """
        self.logger.debug(f"Getting lore for location {location_id}")

        # This would use related_entities filtering
        # For now, return all public memories
        all_memories = await self.world_repo.get_all()
        return [wm for wm in all_memories if wm.is_public][:limit]

    async def get_episode_history(
        self,
        character_id: UUID,
        limit: int = 10,
    ) -> list:
        """
        Get episode timeline for a character.

        Args:
            character_id: Character ID
            limit: Maximum number of results

        Returns:
            List of episodes in chronological order
        """
        episodes = await self.get_character_memories(character_id, limit)
        # Sort by created_at (already sorted in repository)
        return episodes
