"""Core memory processor for capturing, condensing, and promoting memories."""

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from openai import AsyncOpenAI

from ds_common.memory.agents.episode_agent import EpisodeSummary, episode_agent
from ds_common.memory.agents.importance_agent import ImportanceAnalysis, importance_agent
from ds_common.memory.agents.safeguard_agent import SafeguardAnalysis, safeguard_agent
from ds_common.memory.agents.world_memory_agent import WorldNarrative, world_memory_agent
from ds_common.memory.embedding_service import EmbeddingService
from ds_common.metrics.service import get_metrics_service
from ds_common.models.episode_memory import EpisodeMemory
from ds_common.models.memory_settings import MemorySettings
from ds_common.models.memory_snapshot import MemorySnapshot, SnapshotType
from ds_common.models.session_memory import MemoryType, SessionMemory
from ds_common.models.world_memory import WorldMemory
from ds_common.repository.episode_memory import EpisodeMemoryRepository
from ds_common.repository.memory_settings import MemorySettingsRepository
from ds_common.repository.memory_snapshot import MemorySnapshotRepository
from ds_common.repository.session_memory import SessionMemoryRepository
from ds_common.repository.world_memory import WorldMemoryRepository
from ds_discord_bot.postgres_manager import PostgresManager


class MemoryProcessor:
    """Core processor for memory system operations."""

    def __init__(
        self,
        postgres_manager: PostgresManager,
        openai_client: AsyncOpenAI,
        redis_client: Any | None = None,
        embedding_model: str | None = None,
        embedding_dimensions: int | None = None,
    ):
        """
        Initialize the memory processor.

        Args:
            postgres_manager: PostgreSQL manager
            openai_client: OpenAI async client
            redis_client: Optional Redis client for caching
            embedding_model: Embedding model name (optional)
            embedding_dimensions: Embedding dimensions (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.postgres_manager = postgres_manager
        self.embedding_service = EmbeddingService(
            openai_client,
            redis_client,
            model=embedding_model,
            dimensions=embedding_dimensions,
        )
        self.metrics = get_metrics_service()

        # Initialize repositories
        self.session_repo = SessionMemoryRepository(postgres_manager)
        self.episode_repo = EpisodeMemoryRepository(postgres_manager)
        self.world_repo = WorldMemoryRepository(postgres_manager)
        self.snapshot_repo = MemorySnapshotRepository(postgres_manager)
        self.settings_repo = MemorySettingsRepository(postgres_manager)

    async def _get_settings(self) -> MemorySettings:
        """Get memory settings."""
        return await self.settings_repo.get_settings()

    async def capture_session_event(
        self,
        session_id: UUID,
        character_id: UUID,
        memory_type: MemoryType,
        content: dict,
        participants: list[UUID] | None = None,
        location_id: UUID | None = None,
    ) -> UUID:
        """
        Capture and score a session event in real-time.

        Args:
            session_id: Game session ID
            character_id: Character ID who performed the action
            memory_type: Type of memory (dialogue, action, observation)
            content: Event content as dictionary
            participants: List of participant IDs
            location_id: Location ID if applicable

        Returns:
            Memory ID
        """
        self.logger.debug(f"Capturing session event for session {session_id}")

        # Score importance in real-time
        event_text = (
            f"{memory_type}: {content.get('action', 'event')} - {content.get('description', '')}"
        )
        try:
            result = await importance_agent.run(event_text)
            # Handle structured output (result.data) - this is the expected path when output_type works
            # Check both result.data and result.all_data() as pydantic-ai might use different attributes
            analysis = None
            if hasattr(result, "data") and result.data is not None:
                try:
                    analysis = (
                        ImportanceAnalysis.model_validate(result.data)
                        if isinstance(result.data, dict)
                        else result.data
                    )
                    self.logger.debug(
                        f"Importance analysis from structured output (result.data): score={analysis.score}"
                    )
                except (TypeError, ValueError) as e:
                    self.logger.debug(
                        f"result.data exists but couldn't convert to ImportanceAnalysis: {e}, type: {type(result.data)}"
                    )

            # Try result.all_data() if result.data didn't work
            if analysis is None and hasattr(result, "all_data"):
                try:
                    all_data = result.all_data()
                    if all_data:
                        analysis = (
                            ImportanceAnalysis.model_validate(all_data)
                            if isinstance(all_data, dict)
                            else all_data
                        )
                        self.logger.debug(
                            f"Importance analysis from structured output (result.all_data()): score={analysis.score}"
                        )
                except (TypeError, ValueError, AttributeError) as e:
                    self.logger.debug(f"result.all_data() failed: {e}")

            # Fallback: Parse output manually if output_type didn't work
            if analysis is None and hasattr(result, "output") and result.output:
                # Fallback: Parse output manually if output_type didn't work
                import json
                import re

                try:
                    output_text = str(result.output).strip()
                    self.logger.debug(
                        f"Parsing unstructured importance output: {output_text[:200]}..."
                    )

                    data = None

                    # Try 1: Direct JSON parse
                    try:
                        if output_text.startswith("{"):
                            data = json.loads(output_text)
                        else:
                            # Look for JSON object in the text (handle nested braces)
                            brace_count = 0
                            start_idx = output_text.find("{")
                            if start_idx != -1:
                                end_idx = start_idx
                                for i in range(start_idx, len(output_text)):
                                    if output_text[i] == "{":
                                        brace_count += 1
                                    elif output_text[i] == "}":
                                        brace_count -= 1
                                        if brace_count == 0:
                                            end_idx = i + 1
                                            break

                                if brace_count == 0:
                                    json_str = output_text[start_idx:end_idx]
                                    data = json.loads(json_str)
                    except (json.JSONDecodeError, ValueError):
                        pass

                    # Try 2: Parse Python-like keyword arguments (score=0.1 reasoning='...' should_promote=False)
                    if data is None:
                        try:
                            data = {}

                            # Extract score (must be present)
                            score_match = re.search(r"score\s*=\s*([0-9.]+)", output_text)
                            if score_match:
                                data["score"] = float(score_match.group(1))
                            else:
                                raise ValueError("Could not find 'score' field")

                            # Extract reasoning - handle both single and double quotes, with escaped characters
                            # Try to find reasoning='...' or reasoning="..." - need to handle escaped quotes inside
                            reasoning_patterns = [
                                r"reasoning\s*=\s*'((?:[^'\\]|\\.)*)'",  # Single quotes with escapes
                                r'reasoning\s*=\s*"((?:[^"\\]|\\.)*)"',  # Double quotes with escapes
                                r"reasoning\s*=\s*'''((?:[^']|'(?!''))*?)'''",  # Triple single quotes
                                r'reasoning\s*=\s*"""((?:[^"]|"(?!"")*?)"""',  # Triple double quotes
                            ]

                            reasoning_match = None
                            for pattern in reasoning_patterns:
                                reasoning_match = re.search(pattern, output_text, re.DOTALL)
                                if reasoning_match:
                                    break

                            if reasoning_match:
                                reasoning = reasoning_match.group(1)
                                # Decode escape sequences
                                reasoning = reasoning.encode().decode("unicode_escape")
                                data["reasoning"] = reasoning
                            else:
                                raise ValueError("Could not find 'reasoning' field")

                            # Extract should_promote (optional, default False)
                            should_promote_match = re.search(
                                r"should_promote\s*=\s*(True|False)", output_text
                            )
                            if should_promote_match:
                                data["should_promote"] = should_promote_match.group(1) == "True"
                            else:
                                data["should_promote"] = False

                            # Extract tags (optional, default empty list)
                            # Handle both ['tag1', 'tag2'] and ['tag1', 'tag2 (truncated)
                            tags_match = re.search(
                                r"tags\s*=\s*\[(.*?)(?:\]|$)", output_text, re.DOTALL
                            )
                            if tags_match:
                                tags_str = tags_match.group(1)
                                # Extract quoted strings, handling both single and double quotes
                                tag_matches = re.findall(r"['\"]([^'\"]+)['\"]", tags_str)
                                data["tags"] = tag_matches if tag_matches else []
                            else:
                                data["tags"] = []

                            # Extract emotional_valence (optional, default 0.0)
                            valence_match = re.search(
                                r"emotional_valence\s*=\s*([0-9.\-]+)", output_text
                            )
                            if valence_match:
                                data["emotional_valence"] = float(valence_match.group(1))
                            else:
                                data["emotional_valence"] = 0.0

                        except (ValueError, AttributeError, IndexError) as parse_err:
                            self.logger.debug(f"Python-like parsing failed: {parse_err}")
                            raise ValueError(
                                f"Could not parse output in any recognized format: {parse_err}"
                            )

                    # Create analysis from parsed data
                    if data:
                        # Set defaults for missing fields
                        if "score" not in data:
                            data["score"] = 0.5
                        if "reasoning" not in data:
                            data["reasoning"] = "Parsed from unstructured output"
                        if "should_promote" not in data:
                            data["should_promote"] = False
                        if "tags" not in data:
                            data["tags"] = []
                        if "emotional_valence" not in data:
                            data["emotional_valence"] = 0.0

                        analysis = ImportanceAnalysis(**data)
                        self.logger.debug(
                            f"Successfully parsed importance analysis: score={analysis.score}"
                        )
                    else:
                        raise ValueError("No data extracted from output")

                except (json.JSONDecodeError, ValueError, TypeError) as parse_error:
                    self.logger.error(
                        f"Failed to parse importance analysis: {parse_error}. "
                        f"Output: {output_text[:500] if 'output_text' in locals() else 'N/A'}"
                    )
                    raise

            # Final check: if analysis is still None, we couldn't parse the result
            if analysis is None:
                self.logger.error(
                    f"Importance agent result could not be parsed. "
                    f"Has result.data: {hasattr(result, 'data')}, "
                    f"Has result.output: {hasattr(result, 'output')}, "
                    f"Result attributes: {[a for a in dir(result) if not a.startswith('_')]}"
                )
                raise ValueError(
                    f"Could not extract importance analysis from result. Result type: {type(result)}"
                )
        except Exception as e:
            # Log the error with context
            error_msg = str(e)
            if "output_type" in error_msg.lower() or "unknown keyword" in error_msg.lower():
                self.logger.warning(
                    f"Importance agent output_type error (this should not happen with fixed agent): {e}"
                )
            else:
                self.logger.error(
                    f"Failed to score importance for event '{event_text[:100]}...': {e}",
                    exc_info=True,
                )
            # Default analysis on error - this should rarely happen now
            analysis = ImportanceAnalysis(
                score=0.5,
                reasoning=f"Error during analysis: {error_msg}",
                should_promote=False,
                tags=[],
                emotional_valence=0.0,
            )

        # Get settings for expiration
        settings = await self._get_settings()
        expires_at = datetime.now(UTC) + timedelta(hours=settings.session_memory_expiration_hours)

        # Create session memory
        memory = SessionMemory(
            session_id=session_id,
            character_id=character_id,
            timestamp=datetime.now(UTC),
            memory_type=memory_type,
            content=content,
            participants=participants or [],
            location_id=location_id,
            importance_score=analysis.score,
            emotional_valence=analysis.emotional_valence,
            tags=analysis.tags,
            expires_at=expires_at,
            processed=False,
        )

        start_time = time.time()
        created = await self.session_repo.create(memory)
        duration = time.time() - start_time

        self.logger.info(f"Created session memory {created.id} with importance {analysis.score}")

        # Track metrics
        self.metrics.record_memory_capture(memory_type.value)
        self.metrics.record_memory_operation("capture", duration)

        return created.id

    async def condense_session_to_episode(
        self,
        session_id: UUID,
    ) -> UUID:
        """
        Condense session memories into an episode.

        Args:
            session_id: Game session ID

        Returns:
            Episode ID
        """
        self.logger.info(f"Condensing session {session_id} to episode")

        start_time = time.time()
        status = "success"

        try:
            # Get all unprocessed memories for this session
            memories = await self.session_repo.get_by_session(session_id, processed=False)
            if not memories:
                self.logger.warning(f"No unprocessed memories for session {session_id}")
                raise ValueError(f"No unprocessed memories for session {session_id}")

            # Sort by timestamp
            memories.sort(key=lambda m: m.timestamp)

            # Build context for episode agent
            events_text = "\n".join(
                [
                    f"[{m.timestamp}] {m.memory_type}: {m.content.get('action', 'event')} - {m.content.get('description', '')}"
                    for m in memories
                ]
            )

            # Generate episode summary
            try:
                result = await episode_agent.run(events_text)
                summary: EpisodeSummary = result.data
            except Exception as e:
                status = "error"
                self.logger.error(f"Failed to generate episode summary: {e}")
                raise

            # Extract unique characters and locations
            character_ids = list(
                set(
                    [m.character_id for m in memories]
                    + [p for m in memories for p in m.participants]
                )
            )
            location_ids = list(set([m.location_id for m in memories if m.location_id]))

            # Generate embedding
            embedding_text = (
                f"{summary.title}\n{summary.one_sentence_summary}\n{summary.narrative_summary}"
            )
            embedding = await self.embedding_service.generate(embedding_text)

            # Get settings for expiration
            settings = await self._get_settings()
            expires_at = datetime.now(UTC) + timedelta(
                hours=settings.episode_memory_expiration_hours
            )

            # Create episode memory
            episode = EpisodeMemory(
                expires_at=expires_at,
                title=summary.title,
                summary=summary.narrative_summary,
                one_sentence_summary=summary.one_sentence_summary,
                key_moments=[moment.model_dump() for moment in summary.key_moments],
                relationships_changed={
                    "changes": [change.model_dump() for change in summary.relationships_changed]
                },
                themes=summary.themes,
                cliffhangers=summary.cliffhangers,
                characters=character_ids,
                locations=location_ids,
                session_ids=[session_id],
                embedding=embedding,
                importance_score=sum(m.importance_score or 0.0 for m in memories) / len(memories)
                if memories
                else None,
                promoted_to_world=False,
            )

            created = await self.episode_repo.create(episode)

            # Mark session memories as processed
            memory_ids = [m.id for m in memories]
            await self.session_repo.mark_processed(memory_ids)

            self.logger.info(f"Created episode {created.id} from session {session_id}")

            # Track metrics
            duration = time.time() - start_time
            try:
                self.metrics.record_memory_compression(status)
                self.metrics.record_memory_operation("compression", duration)
            except Exception as e:
                self.logger.debug(f"Error recording compression metrics: {e}")

            # Check if episode should be automatically promoted to world memory
            # Promote if importance score >= 0.75
            if created.importance_score and created.importance_score >= 0.75:
                self.logger.info(
                    f"Episode {created.id} has high importance ({created.importance_score:.2f}), "
                    f"automatically promoting to world memory"
                )
                try:
                    # Promote in background to avoid blocking
                    import asyncio

                    asyncio.create_task(self._promote_episode_background(created.id))
                except Exception as e:
                    self.logger.error(
                        f"Failed to schedule automatic promotion for episode {created.id}: {e}"
                    )

            return created.id
        except Exception as e:
            status = "error"
            duration = time.time() - start_time
            self.logger.error(f"Failed to condense session {session_id} to episode: {e}")
            # Track error metrics
            try:
                self.metrics.record_memory_compression(status)
                self.metrics.record_memory_operation("compression", duration)
            except Exception as metric_error:
                self.logger.debug(f"Error recording compression metrics: {metric_error}")
            raise

    async def _promote_episode_background(self, episode_id: UUID) -> None:
        """
        Background task to promote an episode to world memory.
        This is called asynchronously to avoid blocking episode creation.
        """
        try:
            world_memory_id = await self.promote_episode_to_world(episode_id, require_snapshot=True)
            self.logger.info(
                f"Successfully auto-promoted episode {episode_id} to world memory {world_memory_id}"
            )
        except Exception as e:
            self.logger.error(
                f"Failed to auto-promote episode {episode_id} to world memory: {e}", exc_info=True
            )

    async def check_safeguards(
        self,
        episode_id: UUID,
        proposed_narrative: WorldNarrative,
    ) -> SafeguardAnalysis:
        """
        Check if a proposed world memory change requires safeguards.

        Args:
            episode_id: Episode ID being promoted
            proposed_narrative: Proposed world narrative

        Returns:
            Safeguard analysis
        """
        self.logger.debug(f"Checking safeguards for episode {episode_id}")

        context = f"""
        Proposed World Memory:
        Title: {proposed_narrative.title}
        Impact Level: {proposed_narrative.impact_level}
        Description: {proposed_narrative.description}
        Full Narrative: {proposed_narrative.full_narrative[:500]}
        Consequences: {", ".join(proposed_narrative.consequences)}
        """

        try:
            result = await safeguard_agent.run(context)
            analysis: SafeguardAnalysis = result.data
        except Exception as e:
            self.logger.error(f"Failed to run safeguard analysis: {e}")
            # Default to requiring snapshot for high impact
            analysis = SafeguardAnalysis(
                requires_snapshot=proposed_narrative.impact_level in ["major", "world_changing"],
                risk_level="high"
                if proposed_narrative.impact_level in ["major", "world_changing"]
                else "medium",
                detected_threats=[],
                reasoning="Error during analysis, using default",
                recommended_action="Review manually",
            )

        return analysis

    async def create_snapshot(
        self,
        snapshot_type: SnapshotType,
        world_memory_id: UUID | None = None,
        episode_id: UUID | None = None,
        created_reason: str = "",
    ) -> MemorySnapshot:
        """
        Create a snapshot before high-impact world changes.

        Args:
            snapshot_type: Type of snapshot
            world_memory_id: World memory ID if applicable
            episode_id: Episode ID if applicable
            created_reason: Reason for creating snapshot

        Returns:
            Created snapshot
        """
        self.logger.info(f"Creating snapshot for {snapshot_type}")

        # Get current world state
        world_memories = await self.world_repo.get_all()
        snapshot_data = {
            "world_memories": [wm.model_dump() for wm in world_memories],
            "timestamp": datetime.now(UTC).isoformat(),
            "world_memory_id": str(world_memory_id) if world_memory_id else None,
            "episode_id": str(episode_id) if episode_id else None,
        }

        snapshot = MemorySnapshot(
            snapshot_type=snapshot_type,
            snapshot_data=snapshot_data,
            world_memory_id=world_memory_id,
            episode_id=episode_id,
            created_reason=created_reason,
            can_unwind=True,
        )

        created = await self.snapshot_repo.create_snapshot(snapshot)
        self.logger.info(f"Created snapshot {created.id}")

        return created

    async def promote_episode_to_world(
        self,
        episode_id: UUID,
        require_snapshot: bool = True,
    ) -> UUID:
        """
        Promote an episode to world memory.

        Args:
            episode_id: Episode ID to promote
            require_snapshot: Whether to require snapshot for high-impact changes

        Returns:
            World memory ID
        """
        self.logger.info(f"Promoting episode {episode_id} to world memory")

        start_time = time.time()

        # Get episode
        episode = await self.episode_repo.get_by_id(episode_id)
        if not episode:
            raise ValueError(f"Episode {episode_id} not found")

        if episode.promoted_to_world:
            raise ValueError(f"Episode {episode_id} already promoted")

        # Get session memories for context
        session_memories = []
        for session_id in episode.session_ids:
            memories = await self.session_repo.get_by_session(session_id, processed=True)
            session_memories.extend(memories)

        # Build context for world memory agent
        # Include episode locations to help agent identify all relevant locations
        episode_locations_text = ""
        if episode.locations:
            try:
                from ds_common.repository.location_node import LocationNodeRepository

                node_repo = LocationNodeRepository(self.postgres_manager)
                location_names = []
                for loc_id in episode.locations:
                    location_node = await node_repo.get_by_id(loc_id)
                    if location_node:
                        location_names.append(location_node.location_name)
                if location_names:
                    episode_locations_text = f"\nLocations involved: {', '.join(location_names)}"
            except Exception as e:
                self.logger.debug(f"Failed to get location names for episode context: {e}")

        context = f"""
        Episode: {episode.title}
        Summary: {episode.summary}
        Key Moments: {episode.key_moments}
        Themes: {", ".join(episode.themes)}{episode_locations_text}
        """

        # Generate world narrative
        try:
            result = await world_memory_agent.run(context)
            narrative: WorldNarrative = result.data
        except Exception as e:
            self.logger.error(f"Failed to generate world narrative: {e}")
            raise

        # Check safeguards
        safeguard_analysis = await self.check_safeguards(episode_id, narrative)

        # Create snapshot if required
        if require_snapshot and (
            safeguard_analysis.requires_snapshot
            or narrative.impact_level in ["major", "world_changing"]
        ):
            await self.create_snapshot(
                snapshot_type="episode_promotion",
                episode_id=episode_id,
                created_reason=f"Promoting episode with impact level {narrative.impact_level}: {safeguard_analysis.reasoning}",
            )

        # Merge episode locations with agent-extracted locations
        # Ensure all locations from episode are preserved in world memory
        merged_related_entities = (
            narrative.related_entities.copy() if narrative.related_entities else {}
        )

        # Get location names from episode's location_ids
        episode_location_names = []
        if episode.locations:
            try:
                from ds_common.repository.location_node import LocationNodeRepository

                node_repo = LocationNodeRepository(self.postgres_manager)
                for loc_id in episode.locations:
                    location_node = await node_repo.get_by_id(loc_id)
                    if location_node:
                        episode_location_names.append(location_node.location_name)
            except Exception as e:
                self.logger.debug(f"Failed to get location names for merging: {e}")

        # Merge locations: agent-extracted + episode locations
        if "locations" not in merged_related_entities:
            merged_related_entities["locations"] = []

        # Add episode locations that aren't already in agent's list
        agent_locations = [
            loc.lower() if isinstance(loc, str) else str(loc).lower()
            for loc in merged_related_entities.get("locations", [])
        ]
        for loc_name in episode_location_names:
            if loc_name.lower() not in agent_locations:
                merged_related_entities["locations"].append(loc_name)

        # Also preserve location_ids for canonical tracking
        # Store as strings in related_entities for compatibility
        if episode.locations:
            if "location_ids" not in merged_related_entities:
                merged_related_entities["location_ids"] = []
            # Add location IDs as strings
            for loc_id in episode.locations:
                loc_id_str = str(loc_id)
                if loc_id_str not in merged_related_entities["location_ids"]:
                    merged_related_entities["location_ids"].append(loc_id_str)

        # Generate embedding
        embedding_text = f"{narrative.title}\n{narrative.description}\n{narrative.full_narrative}"
        embedding = await self.embedding_service.generate(embedding_text)

        # Create world memory with merged entities
        world_memory = WorldMemory(
            memory_category=None,  # Can be set based on narrative
            title=narrative.title,
            description=narrative.description,
            full_narrative=narrative.full_narrative,
            related_entities=merged_related_entities,  # Use merged entities with all locations
            source_episodes=[episode_id],
            consequences=narrative.consequences,
            embedding=embedding,
            tags=narrative.tags,
            impact_level=narrative.impact_level,
            is_public=narrative.is_public,
            discovery_requirements=narrative.discovery_requirements,
        )

        created = await self.world_repo.create(world_memory)

        # Mark episode as promoted
        episode.promoted_to_world = True
        await self.episode_repo.update(episode)

        self.logger.info(f"Promoted episode {episode_id} to world memory {created.id}")

        # Track metrics
        duration = time.time() - start_time
        self.metrics.record_memory_episode_promotion()
        self.metrics.record_memory_operation("promotion", duration)

        return created.id
