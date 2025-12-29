"""
Intelligent memory compression service to reduce AI overhead.

Strategies:
1. Semantic relevance filtering (use embeddings to find relevant memories)
2. Importance-based prioritization (high-importance memories first)
3. Temporal compression (summarize older memories, keep recent detailed)
4. Deduplication (remove similar/redundant memories)
5. Token-aware limiting (ensure total context stays within limits)
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from ds_common.memory.embedding_service import EmbeddingService
from ds_common.models.session_memory import SessionMemory
from ds_common.repository.session_memory import SessionMemoryRepository
from ds_discord_bot.postgres_manager import PostgresManager


class MemoryCompressor:
    """
    Service for intelligently compressing and filtering memories to reduce AI overhead.
    """

    def __init__(
        self,
        postgres_manager: PostgresManager,
        embedding_service: EmbeddingService,
    ):
        """
        Initialize the memory compressor.

        Args:
            postgres_manager: PostgreSQL manager
            embedding_service: Embedding service for semantic search
        """
        self.logger = logging.getLogger(__name__)
        self.postgres_manager = postgres_manager
        self.embedding_service = embedding_service
        self.session_repo = SessionMemoryRepository(postgres_manager)

    async def get_compressed_session_context(
        self,
        session_id: UUID,
        query: str | None = None,
        character_id: UUID | None = None,
        max_memories: int = 8,
        max_recent_memories: int = 5,
        importance_threshold: float = 0.3,
    ) -> str:
        """
        Get compressed session context with intelligent filtering and summarization.

        Args:
            session_id: Game session ID
            query: Optional query text for semantic relevance filtering
            character_id: Optional character ID to filter by
            max_memories: Maximum number of memories to include
            max_recent_memories: Maximum number of recent memories to keep detailed
            importance_threshold: Minimum importance score (0.0-1.0)

        Returns:
            Compressed context string
        """
        # Get all unprocessed memories for this session
        all_memories = await self.session_repo.get_by_session(session_id, processed=False)

        if not all_memories:
            return ""

        # Sort by timestamp (most recent first)
        all_memories.sort(key=lambda m: m.timestamp, reverse=True)

        # Filter by character if provided
        if character_id:
            all_memories = [
                m
                for m in all_memories
                if m.character_id == character_id or character_id in m.participants
            ]

        # Separate recent and older memories
        now = datetime.now(UTC)
        # Get recent cutoff from game_settings (DB), fallback to config, then default
        recent_cutoff_minutes = 30  # Default fallback
        try:
            from ds_common.repository.game_settings import GameSettingsRepository

            settings_repo = GameSettingsRepository(self.postgres_manager)
            game_settings = await settings_repo.get_settings()
            if game_settings:
                recent_cutoff_minutes = game_settings.memory_recent_cutoff_minutes
        except Exception:
            # Fallback to config if DB access fails
            try:
                from ds_common.config_bot import get_config

                config = get_config()
                recent_cutoff_minutes = config.memory_recent_cutoff_minutes
            except Exception:
                recent_cutoff_minutes = 30  # Final fallback
        recent_cutoff = now - timedelta(minutes=recent_cutoff_minutes)

        recent_memories = [m for m in all_memories if m.timestamp >= recent_cutoff]
        older_memories = [m for m in all_memories if m.timestamp < recent_cutoff]

        # Always include recent memories (detailed)
        selected_memories = recent_memories[:max_recent_memories]

        # For older memories, use intelligent filtering
        if query:
            # Use semantic search to find relevant older memories
            relevant_older = await self._semantic_filter_memories(
                older_memories, query, max_memories - len(selected_memories)
            )
            selected_memories.extend(relevant_older)
        else:
            # Filter by importance and limit count
            filtered_older = [
                m
                for m in older_memories
                if m.importance_score and m.importance_score >= importance_threshold
            ]
            selected_memories.extend(filtered_older[: max_memories - len(selected_memories)])

        # Deduplicate similar memories
        selected_memories = await self._deduplicate_memories(selected_memories)

        # Sort chronologically for context
        selected_memories.sort(key=lambda m: m.timestamp)

        # Format into compressed context
        return await self._format_compressed_context(selected_memories, len(all_memories))

    async def _semantic_filter_memories(
        self,
        memories: list[SessionMemory],
        query: str,
        limit: int,
    ) -> list[SessionMemory]:
        """
        Filter memories by semantic relevance to query.

        Args:
            memories: List of memories to filter
            query: Query text
            limit: Maximum number to return

        Returns:
            List of most relevant memories
        """
        if not memories:
            return []

        # Generate query embedding
        query_embedding = await self.embedding_service.generate(query)

        # Prepare memory texts for batch embedding generation
        memory_texts = []
        memory_map = []

        for memory in memories:
            memory_text = (
                f"{memory.content.get('action', '')} {memory.content.get('description', '')}"
            )

            if memory_text.strip():
                memory_texts.append(memory_text)
                memory_map.append(memory)

        if not memory_texts:
            return []

        # Generate embeddings in batch (more efficient)
        memory_embeddings = await self.embedding_service.generate_batch(memory_texts)

        # Calculate similarity for each memory
        memory_scores = []
        for memory, memory_embedding in zip(memory_map, memory_embeddings):
            # Calculate cosine similarity
            similarity = self._cosine_similarity(query_embedding, memory_embedding)

            # Combine with importance score if available
            combined_score = similarity
            if memory.importance_score:
                combined_score = (similarity * 0.6) + (memory.importance_score * 0.4)

            memory_scores.append((memory, combined_score))

        # Sort by combined score and return top results
        memory_scores.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in memory_scores[:limit]]

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score (0.0 to 1.0)
        """
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    async def _deduplicate_memories(
        self,
        memories: list[SessionMemory],
        similarity_threshold: float = 0.85,
    ) -> list[SessionMemory]:
        """
        Remove duplicate or very similar memories.

        Args:
            memories: List of memories
            similarity_threshold: Similarity threshold for deduplication (0.0-1.0)

        Returns:
            Deduplicated list of memories
        """
        if len(memories) <= 1:
            return memories

        # Group memories by similarity
        unique_memories = []
        seen_texts = set()

        for memory in memories:
            # Create a simple text signature
            action = memory.content.get("action", "")
            description = memory.content.get("description", "")
            text_sig = f"{action} {description}".lower().strip()[:100]

            # Simple deduplication: skip if very similar text seen recently
            is_duplicate = False
            for seen in seen_texts:
                # Simple similarity check (in production, use embeddings)
                if self._text_similarity(text_sig, seen) > similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_memories.append(memory)
                seen_texts.add(text_sig)

        return unique_memories

    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Simple text similarity using word overlap.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0.0 to 1.0)
        """
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    async def _format_compressed_context(
        self,
        memories: list[SessionMemory],
        total_memories: int,
    ) -> str:
        """
        Format memories into compressed context string.

        Args:
            memories: List of memories to format
            total_memories: Total number of memories (for context)

        Returns:
            Formatted context string
        """
        if not memories:
            return ""

        lines = []
        current_location = None
        location_region = None

        # Check most recent memories first for location (reverse order)
        for memory in reversed(memories):
            action = memory.content.get("action", "event")
            description = memory.content.get("description", "")
            response_text = memory.content.get("response", "")

            # Extract location from response or use location_id if available
            if not current_location:
                if memory.location_id:
                    # Location ID is stored, we can look up the region
                    # For now, extract from response text
                    pass

                if response_text:
                    location_keywords = [
                        "Agrihaven",
                        "Neotopia",
                        "Undergrid",
                        "Driftmark",
                        "Skyward Nexus",
                        "tunnel",
                        "corridor",
                        "sector",
                        "Corporate Sector",
                        "Residential District",
                        "Tech Plaza",
                        "Sector 7",
                        "Sector 12",
                        "Power Generation",
                        "Waste Management",
                    ]
                    for keyword in location_keywords:
                        if keyword.lower() in response_text.lower():
                            current_location = keyword
                            break

            # Format memory line based on importance score
            # High importance events may promote to episode/world memory, so preserve more detail
            importance = memory.importance_score or 0.0

            if importance >= 0.7:
                # High importance: Include full GM response (up to 1000 chars)
                # These events are likely to be promoted, so preserve rich narrative context
                gm_content = response_text if response_text else description
                if gm_content:
                    truncated = gm_content[:1000] + "..." if len(gm_content) > 1000 else gm_content
                    lines.append(f"- {action}: {truncated}")
                else:
                    lines.append(f"- {action}")
            elif importance >= 0.4:
                # Medium importance: Include summarized/truncated GM dialog (400-600 chars)
                # Prefer response if available, fallback to description
                gm_content = response_text if response_text else description
                if gm_content:
                    # Use description as summary if available and different, otherwise truncate response
                    if (
                        description
                        and description != response_text
                        and len(description) < len(response_text)
                    ):
                        # Description is a summary, use it
                        truncated = (
                            description[:600] + "..." if len(description) > 600 else description
                        )
                    else:
                        # Truncate the response
                        truncated = (
                            gm_content[:600] + "..." if len(gm_content) > 600 else gm_content
                        )
                    lines.append(f"- {action}: {truncated}")
                else:
                    lines.append(f"- {action}")
            else:
                # Low importance: Brief description only (200 chars)
                # These are routine events, minimal context needed
                if description:
                    truncated = description[:200] + "..." if len(description) > 200 else description
                    lines.append(f"- {action}: {truncated}")
                else:
                    lines.append(f"- {action}")

        # Reverse lines back to chronological order
        lines.reverse()

        context = f"[RECENT SESSION CONTEXT ({len(memories)}/{total_memories} memories):\n"
        context += "\n".join(lines)

        if current_location:
            location_info = f"[CURRENT LOCATION: {current_location}"
            if location_region:
                location_info += f", {location_region}"
            location_info += "]"
            context += f"\n{location_info}"

        context += "\nUse this to maintain continuity.]\n\n"

        return context

    async def extract_environmental_items(
        self,
        session_id: UUID,
        character_id: UUID | None = None,
        lookback_minutes: int = 30,
    ) -> str:
        """
        Extract environmental items mentioned in recent GM responses.
        This helps track items that players can interact with.

        Args:
            session_id: Game session ID
            character_id: Optional character ID to filter by
            lookback_minutes: How many minutes back to look for items

        Returns:
            Formatted string with environmental items, or empty string if none found
        """
        # Get recent memories
        all_memories = await self.session_repo.get_by_session(session_id, processed=False)
        if not all_memories:
            return ""

        # Filter by character if provided
        if character_id:
            all_memories = [
                m
                for m in all_memories
                if m.character_id == character_id or character_id in m.participants
            ]

        # Filter by time (recent memories only)
        now = datetime.now(UTC)
        recent_cutoff = now - timedelta(minutes=lookback_minutes)
        recent_memories = [m for m in all_memories if m.timestamp >= recent_cutoff]

        if not recent_memories:
            return ""

        # Extract items from GM responses
        # Look for common item patterns in response text
        items_mentioned = set()
        item_keywords = [
            "wrench",
            "tool",
            "weapon",
            "device",
            "item",
            "object",
            "gear",
            "equipment",
            "pick",
            "grab",
            "take",
            "collect",
            "find",
            "lying",
            "on the ground",
            "nearby",
            "scattered",
            "abandoned",
            "discarded",
            "available",
            "can be",
            "you can use",
            "a ",
            "an ",
            "the ",
            "nearby ",
            "near ",
            "beside ",
            "next to ",
            "on ",
            "in ",
        ]

        # Common item types to look for
        item_types = [
            "wrench",
            "screwdriver",
            "hammer",
            "knife",
            "gun",
            "pistol",
            "rifle",
            "sword",
            "key",
            "card",
            "chip",
            "device",
            "tool",
            "gear",
            "equipment",
            "weapon",
            "battery",
            "cable",
            "wire",
            "panel",
            "console",
            "terminal",
            "datapad",
        ]

        for memory in recent_memories:
            response_text = memory.content.get("response", "")
            description = memory.content.get("description", "")

            # Combine response and description
            text_to_search = f"{response_text} {description}".lower()

            # Method 1: Look for explicit item type mentions
            for item_type in item_types:
                # Look for patterns like "a wrench", "the wrench", "wrench lying", etc.
                patterns = [
                    f" {item_type} ",
                    f" {item_type},",
                    f" {item_type}.",
                    f" {item_type}'",
                    f"a {item_type}",
                    f"an {item_type}",
                    f"the {item_type}",
                ]
                if any(pattern in text_to_search for pattern in patterns):
                    items_mentioned.add(item_type.capitalize())

            # Method 2: Look for item keywords with context
            words = text_to_search.split()
            for i, word in enumerate(words):
                # Check if word is near item keywords
                context_window = words[max(0, i - 3) : min(len(words), i + 4)]
                context_str = " ".join(context_window)

                # Check for explicit item mentions with action verbs
                action_patterns = [
                    "pick up",
                    "grab",
                    "take",
                    "collect",
                    "find",
                    "lying",
                    "on the ground",
                    "nearby",
                    "scattered",
                    "abandoned",
                    "discarded",
                    "available",
                    "can use",
                ]
                if any(pattern in context_str for pattern in action_patterns):
                    # Try to extract the item name (word before or after keyword)
                    if i > 0:
                        potential_item = words[i - 1].strip(".,!?;:")
                        if len(potential_item) > 2 and potential_item.isalpha():
                            items_mentioned.add(potential_item.capitalize())
                    if i < len(words) - 1:
                        potential_item = words[i + 1].strip(".,!?;:")
                        if len(potential_item) > 2 and potential_item.isalpha():
                            items_mentioned.add(potential_item.capitalize())

        if not items_mentioned:
            return ""

        # Format as context
        items_list = sorted(list(items_mentioned))
        return f"[ENVIRONMENTAL ITEMS MENTIONED RECENTLY: {', '.join(items_list)}]\n[These items may be available for the player to interact with. When a player attempts to pick up or use an item you've mentioned, use find_and_collect_world_item or add_character_item as appropriate.]\n\n"

    async def compress_episode_summaries(
        self,
        episodes: list[Any],
        limit: int = 3,
    ) -> str:
        """
        Compress episode summaries into a concise format.

        Args:
            episodes: List of episode memories
            limit: Maximum number of episodes to include

        Returns:
            Compressed episode context string
        """
        if not episodes:
            return ""

        # Sort by created_at (most recent first)
        sorted_episodes = sorted(episodes, key=lambda e: e.created_at, reverse=True)[:limit]

        lines = []
        for ep in sorted_episodes:
            title = ep.title or "Episode"
            summary = ep.one_sentence_summary or ep.summary or ""

            # Truncate if too long
            if summary and len(summary) > 120:
                summary = summary[:120] + "..."

            if summary:
                lines.append(f"- {title}: {summary}")
            else:
                lines.append(f"- {title}")

        if lines:
            return f"[CHARACTER EPISODE HISTORY:\n{chr(10).join(lines)}\n]\n\n"

        return ""
