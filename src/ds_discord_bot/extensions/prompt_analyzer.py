"""
Prompt context analyzer for determining which prompt modules to load based on message and game context.

Uses a hybrid approach:
1. Fast keyword matching for obvious cases
2. AI-based semantic classification for uncertain/edge cases
"""

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ds_common.models.character import Character
    from ds_common.models.game_session import GameSession
    from ds_discord_bot.postgres_manager import PostgresManager

logger = logging.getLogger(__name__)


def _get_config_value(
    key_path: tuple[str, ...], default: str | bool | float | int
) -> str | bool | float | int:
    """Get configuration value from config system or environment variables."""
    try:
        from ds_common.config_bot import get_config

        config = get_config()
        value = config.get(*key_path, default=default)
        return value
    except ImportError:
        # Fallback to environment variables if config not available
        import os

        # Map key paths to environment variable names
        env_map = {
            ("prompt_analyzer", "use_ai"): (
                "DS_PROMPT_ANALYZER_USE_AI",
                "DB_PROMPT_ANALYZER_USE_AI",
                "true",
            ),
            ("prompt_analyzer", "ai_threshold"): (
                "DS_PROMPT_ANALYZER_AI_THRESHOLD",
                "DB_PROMPT_ANALYZER_AI_THRESHOLD",
                "0.7",
            ),
            ("prompt_analyzer", "ai_validate"): (
                "DS_PROMPT_ANALYZER_AI_VALIDATE",
                "DB_PROMPT_ANALYZER_AI_VALIDATE",
                "true",
            ),
            ("prompt_analyzer", "embedding_model"): (
                "DS_PROMPT_ANALYZER_EMBEDDING_MODEL",
                "DB_PROMPT_ANALYZER_EMBEDDING_MODEL",
                "text-embedding-3-small",
            ),
            ("prompt_analyzer", "embedding_dimensions"): (
                "DS_PROMPT_ANALYZER_EMBEDDING_DIMENSIONS",
                "DB_PROMPT_ANALYZER_EMBEDDING_DIMENSIONS",
                "1536",
            ),
            ("prompt_analyzer", "keywords_only"): (
                "DS_PROMPT_ANALYZER_KEYWORDS_ONLY",
                "DB_PROMPT_ANALYZER_KEYWORDS_ONLY",
                "false",
            ),
            ("prompt_analyzer", "ai_fallback_only"): (
                "DS_PROMPT_ANALYZER_AI_FALLBACK_ONLY",
                "DB_PROMPT_ANALYZER_AI_FALLBACK_ONLY",
                "false",
            ),
        }

        if key_path in env_map:
            new_name, old_name, fallback = env_map[key_path]
            value = os.getenv(new_name) or os.getenv(old_name) or fallback
            if isinstance(default, bool):
                return value.lower() == "true"
            if isinstance(default, float):
                return float(value)
            if isinstance(default, int):
                return int(value)
            return value
        return default


@dataclass
class PromptAnalyzerConfig:
    """Configuration for prompt context analyzer."""

    # AI Classification Settings
    use_ai_classification: bool = field(
        default_factory=lambda: _get_config_value(("prompt_analyzer", "use_ai"), True)
    )
    ai_confidence_threshold: float = field(
        default_factory=lambda: _get_config_value(("prompt_analyzer", "ai_threshold"), 0.7)
    )
    use_ai_for_validation: bool = field(
        default_factory=lambda: _get_config_value(("prompt_analyzer", "ai_validate"), True)
    )

    # Embedding Model Settings
    embedding_model: str = field(
        default_factory=lambda: _get_config_value(
            ("prompt_analyzer", "embedding_model"), "text-embedding-3-small"
        )
    )
    embedding_dimensions: int = field(
        default_factory=lambda: _get_config_value(("prompt_analyzer", "embedding_dimensions"), 1536)
    )

    # Performance Settings
    always_use_keywords: bool = field(
        default_factory=lambda: _get_config_value(("prompt_analyzer", "keywords_only"), False)
    )
    ai_fallback_only: bool = field(
        default_factory=lambda: _get_config_value(("prompt_analyzer", "ai_fallback_only"), False)
    )


class PromptContextAnalyzer:
    """Analyzes player messages and game context to determine which prompt modules should be loaded."""

    def __init__(
        self,
        postgres_manager: "PostgresManager",
        config: PromptAnalyzerConfig | None = None,
        embedding_service=None,
    ):
        """
        Initialize the prompt context analyzer.

        Args:
            postgres_manager: Database manager
            config: Configuration for the analyzer (uses defaults if None)
            embedding_service: Optional embedding service for AI classification
        """
        self.postgres_manager = postgres_manager
        self.config = config or PromptAnalyzerConfig()
        self.embedding_service = embedding_service

        # Intent examples for each module category (used for semantic matching)
        self.intent_examples = {
            "inventory_rules": [
                "use my bomb",
                "deploy the warhead",
                "activate the device",
                "equip my weapon",
                "drink a potion",
                "use an item from inventory",
            ],
            "quest_rules": [
                "what quests do I have",
                "show my missions",
                "check my quest log",
                "what tasks am I on",
                "my objectives",
                "active missions",
                "show my assignments",
                "what jobs do I have",
            ],
            "combat_rules": [
                "attack the enemy",
                "fight the opponent",
                "strike with my weapon",
                "defend against attack",
                "dodge the incoming strike",
                "check my health status",
            ],
            "travel_rules": [
                "travel to Neotopia",
                "go to the Corporate Sector",
                "walk to Agrihaven",
                "move to a new location",
                "visit the Undergrid",
                "head to Driftmark",
            ],
            "calendar_system": [
                "what time is it",
                "what day is it",
                "what month are we in",
                "what year is it",
                "when is the next event",
                "how long until",
            ],
            "faction_info": [
                "tell me about the Quillfangs",
                "what do you know about Night Prowlers",
                "information about the Obsidian Beak Guild",
                "who are the Berserking Bruins",
                "faction dynamics",
            ],
        }

        # Cache for intent embeddings (computed once)
        self._intent_embeddings_cache: dict[str, list[float]] = {}

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

    def _detects_combat(self, message: str) -> bool:
        """Detect if message involves combat."""
        message_lower = message.lower()
        combat_keywords = [
            "attack",
            "fight",
            "combat",
            "battle",
            "strike",
            "hit",
            "damage",
            "health",
            "stamina",
            "armor",
            "weapon",
            "kill",
            "defeat",
            "enemy",
            "opponent",
            "defend",
            "dodge",
            "block",
            "parry",
        ]
        return any(keyword in message_lower for keyword in combat_keywords)

    def _detects_travel(self, message: str) -> bool:
        """Detect if message involves travel or location changes."""
        message_lower = message.lower()
        travel_keywords = [
            "travel",
            "go to",
            "move to",
            "walk to",
            "run to",
            "head to",
            "journey",
            "visit",
            "enter",
            "leave",
            "arrive",
            "reach",
            "location",
            "place",
            "area",
            "district",
            "sector",
            "city",
        ]
        # Also check for city/location names
        location_names = [
            "neotopia",
            "agrihaven",
            "driftmark",
            "skyward nexus",
            "undergrid",
            "underbelly",
            "corporate sector",
            "residential district",
        ]
        return any(keyword in message_lower for keyword in travel_keywords + location_names)

    def _detects_time_question(self, message: str) -> bool:
        """Detect if message asks about time or calendar."""
        message_lower = message.lower()
        time_keywords = [
            "what time",
            "what day",
            "what month",
            "what year",
            "what date",
            "when is",
            "time is",
            "day is",
            "month is",
            "calendar",
            "how long",
            "how much time",
        ]
        return any(keyword in message_lower for keyword in time_keywords)

    def _detects_faction_mention(self, message: str) -> bool:
        """Detect if message mentions factions."""
        message_lower = message.lower()
        faction_names = [
            "quillfangs",
            "night prowlers",
            "slicktails",
            "serpent's embrace",
            "obsidian beak",
            "berserking bruins",
            "spine baroness",
        ]
        return any(faction in message_lower for faction in faction_names)

    def _detects_quest_mention(self, message: str) -> bool:
        """Detect if message asks about quests, missions, tasks, objectives, etc."""
        message_lower = message.lower()
        quest_keywords = [
            "quest",
            "quests",
            "quest log",
            "active quest",
            "completed quest",
            "mission",
            "missions",
            "mission log",
            "active mission",
            "task",
            "tasks",
            "task list",
            "my task",
            "active task",
            "objective",
            "objectives",
            "my objective",
            "active objective",
            "assignment",
            "assignments",
            "my assignment",
            "job",
            "jobs",
            "my job",
            "active job",
            # Abandonment keywords
            "abandon quest",
            "drop quest",
            "cancel quest",
            "remove quest",
            "abandon mission",
            "drop mission",
            "cancel mission",
            "give up on",
            "stop working on",
        ]
        return any(keyword in message_lower for keyword in quest_keywords)

    async def _is_in_active_encounter(self, game_session: "GameSession") -> bool:
        """Check if game session has an active encounter."""
        try:
            from ds_common.repository.encounter import EncounterRepository

            encounter_repo = EncounterRepository(self.postgres_manager)
            active_encounter = await encounter_repo.get_active_encounter(game_session)
            return active_encounter is not None
        except Exception as e:
            logger.debug(f"Failed to check active encounter: {e}")
            return False

    async def _get_location_type(self, character: "Character") -> str | None:
        """Get the type of the character's current location."""
        if not character or not character.current_location:
            return None

        try:
            from ds_common.repository.location_node import LocationNodeRepository

            node_repo = LocationNodeRepository(self.postgres_manager)
            location_node = await node_repo.get_by_id(character.current_location)
            if location_node:
                return location_node.location_type.lower()
        except Exception as e:
            logger.debug(f"Failed to get location type: {e}")

        return None

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (0-1, higher = more similar)
        """
        import math

        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    async def _get_intent_embeddings(self) -> dict[str, list[float]]:
        """
        Get or compute embeddings for intent examples.

        Returns:
            Dictionary mapping intent category to embedding vector
        """
        if self._intent_embeddings_cache:
            return self._intent_embeddings_cache

        if not self.embedding_service:
            return {}

        # Compute embeddings for all intent examples
        all_examples = []
        example_map = {}  # Maps index to (category, example)

        for category, examples in self.intent_examples.items():
            for example in examples:
                all_examples.append(example)
                example_map[len(all_examples) - 1] = (category, example)

        if not all_examples:
            return {}

        try:
            # Generate embeddings in batch
            embeddings = await self.embedding_service.generate_batch(all_examples)

            # Average embeddings per category
            category_embeddings: dict[str, list[list[float]]] = {}
            for idx, embedding in enumerate(embeddings):
                category, _ = example_map[idx]
                if category not in category_embeddings:
                    category_embeddings[category] = []
                category_embeddings[category].append(embedding)

            # Average the embeddings for each category
            for category, emb_list in category_embeddings.items():
                if emb_list:
                    # Average all embeddings for this category
                    avg_embedding = [
                        sum(emb[i] for emb in emb_list) / len(emb_list)
                        for i in range(len(emb_list[0]))
                    ]
                    self._intent_embeddings_cache[category] = avg_embedding

            logger.info(
                f"Computed intent embeddings for {len(self._intent_embeddings_cache)} categories"
            )
        except Exception as e:
            logger.warning(f"Failed to compute intent embeddings: {e}")
            return {}

        return self._intent_embeddings_cache

    async def _classify_with_ai(self, message: str) -> dict[str, float]:
        """
        Classify message intent using AI embeddings.

        Args:
            message: Player message to classify

        Returns:
            Dictionary mapping intent categories to confidence scores (0-1)
        """
        if not self.embedding_service or not self.config.use_ai_classification:
            logger.debug("AI classification disabled or embedding service unavailable")
            return {}

        try:
            # Get intent embeddings
            intent_embeddings = await self._get_intent_embeddings()
            if not intent_embeddings:
                logger.debug("No intent embeddings available for AI classification")
                return {}

            # Generate embedding for message
            message_embedding = await self.embedding_service.generate(message)

            # Calculate similarity to each intent category
            scores = {}
            for category, category_embedding in intent_embeddings.items():
                similarity = self._cosine_similarity(message_embedding, category_embedding)
                if similarity >= self.config.ai_confidence_threshold:
                    scores[category] = similarity

            if scores:
                logger.info(f"AI classification detected intents: {scores}")
            else:
                logger.debug(
                    f"AI classification: no intents above threshold ({self.config.ai_confidence_threshold})"
                )
            return scores
        except Exception as e:
            logger.warning(f"Failed to classify message with AI: {e}")
            return {}

    def _get_keyword_results(self, message: str) -> dict[str, bool]:
        """
        Get keyword matching results for all categories.

        Args:
            message: Player message

        Returns:
            Dictionary mapping categories to boolean (True if keyword match found)
        """
        results = {
            "inventory_rules": self._detects_item_usage(message),
            "quest_rules": self._detects_quest_mention(message),
            "combat_rules": self._detects_combat(message),
            "travel_rules": self._detects_travel(message),
            "calendar_system": self._detects_time_question(message),
            "faction_info": self._detects_faction_mention(message),
        }
        matched = [cat for cat, matched in results.items() if matched]
        if matched:
            logger.info(f"Keyword matching detected: {', '.join(matched)}")
        return results

    async def analyze(
        self,
        message: str,
        character: "Character | None",
        game_session: "GameSession",
    ) -> set[str]:
        """
        Analyze message and context to determine which prompt modules to load.

        Uses hybrid approach:
        1. Keyword matching (fast path)
        2. AI classification (for validation or when keywords fail)

        Args:
            message: The player's message
            character: The character taking action (if any)
            game_session: The current game session

        Returns:
            Set of module names to load
        """
        modules = {"core_identity", "formatting_guidelines", "content_guidelines"}

        # Always include setting and narrative for context
        modules.add("setting_lore")
        modules.add("narrative_guidelines")

        # CRITICAL: Always include inventory_rules when a character exists
        # This prevents the GM from inventing items in opening scenes and narrative descriptions
        # Inventory rules must be present whenever there's a character, regardless of message content
        if character:
            modules.add("inventory_rules")

        # Get keyword matching results
        keyword_results = self._get_keyword_results(message)

        # Get AI classification results (if enabled)
        ai_results = {}
        if self.config.use_ai_classification and not self.config.always_use_keywords:
            ai_results = await self._classify_with_ai(message)

        # Hybrid decision logic
        if self.config.always_use_keywords:
            # Keywords only mode
            if keyword_results.get("inventory_rules"):
                modules.add("inventory_rules")
            if keyword_results.get("quest_rules"):
                modules.add("quest_rules")
            if keyword_results.get("combat_rules"):
                modules.add("combat_rules")
                modules.add("encounter_types")
            if keyword_results.get("travel_rules"):
                modules.add("travel_rules")
                modules.add("world_consistency")
            if keyword_results.get("calendar_system"):
                modules.add("calendar_system")
            if keyword_results.get("faction_info"):
                modules.add("faction_info")
        elif self.config.ai_fallback_only:
            # AI only when keywords fail
            for category, keyword_match in keyword_results.items():
                if keyword_match:
                    if category == "inventory_rules":
                        modules.add("inventory_rules")
                    elif category == "quest_rules":
                        modules.add("quest_rules")
                    elif category == "combat_rules":
                        modules.add("combat_rules")
                        modules.add("encounter_types")
                    elif category == "travel_rules":
                        modules.add("travel_rules")
                        modules.add("world_consistency")
                    elif category == "calendar_system":
                        modules.add("calendar_system")
                    elif category == "faction_info":
                        modules.add("faction_info")

            # Use AI for categories where keywords didn't match
            for category, ai_score in ai_results.items():
                if not keyword_results.get(category, False):
                    if category == "inventory_rules":
                        modules.add("inventory_rules")
                    elif category == "quest_rules":
                        modules.add("quest_rules")
                    elif category == "combat_rules":
                        modules.add("combat_rules")
                        modules.add("encounter_types")
                    elif category == "travel_rules":
                        modules.add("travel_rules")
                        modules.add("world_consistency")
                    elif category == "calendar_system":
                        modules.add("calendar_system")
                    elif category == "faction_info":
                        modules.add("faction_info")
        else:
            # Hybrid: Use keywords first, validate/refine with AI
            for category, keyword_match in keyword_results.items():
                ai_score = ai_results.get(category, 0.0)

                # If keywords match, use it (unless AI strongly disagrees)
                if keyword_match:
                    if not self.config.use_ai_for_validation or ai_score >= (
                        1.0 - self.config.ai_confidence_threshold
                    ):
                        if category == "inventory_rules":
                            modules.add("inventory_rules")
                        elif category == "quest_rules":
                            modules.add("quest_rules")
                        elif category == "combat_rules":
                            modules.add("combat_rules")
                            modules.add("encounter_types")
                        elif category == "travel_rules":
                            modules.add("travel_rules")
                            modules.add("world_consistency")
                        elif category == "calendar_system":
                            modules.add("calendar_system")
                        elif category == "faction_info":
                            modules.add("faction_info")
                # If keywords don't match but AI does, use AI
                elif ai_score >= self.config.ai_confidence_threshold:
                    if category == "inventory_rules":
                        modules.add("inventory_rules")
                    elif category == "quest_rules":
                        modules.add("quest_rules")
                    elif category == "combat_rules":
                        modules.add("combat_rules")
                        modules.add("encounter_types")
                    elif category == "travel_rules":
                        modules.add("travel_rules")
                        modules.add("world_consistency")
                    elif category == "calendar_system":
                        modules.add("calendar_system")
                    elif category == "faction_info":
                        modules.add("faction_info")

        # Combat/encounter detection (game state based)
        in_encounter = await self._is_in_active_encounter(game_session)
        if in_encounter:
            modules.add("combat_rules")
            modules.add("encounter_types")

        # Location-specific rules
        if character:
            location_type = await self._get_location_type(character)
            if location_type:
                # Add location-specific rules for certain location types
                if location_type in ["undergrid", "undergrid sector", "undergrid district"]:
                    modules.add("location_specific")
                # Could add more location-specific rules here

        logger.info(f"Selected prompt modules ({len(modules)}): {', '.join(sorted(modules))}")
        return modules
