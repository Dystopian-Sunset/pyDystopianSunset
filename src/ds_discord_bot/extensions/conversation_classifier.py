"""
Conversation actionability classifier for determining if messages require GM involvement.

Uses a hybrid approach:
1. Fast keyword matching for obvious cases
2. AI-based semantic classification for uncertain/edge cases
"""

import logging
from dataclasses import dataclass, field
from typing import Literal

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
            ("conversation_classifier", "enabled"): ("DS_CONVERSATION_CLASSIFIER_ENABLED", "true"),
            ("conversation_classifier", "use_ai"): ("DS_CONVERSATION_CLASSIFIER_USE_AI", "true"),
            ("conversation_classifier", "ai_threshold"): (
                "DS_CONVERSATION_CLASSIFIER_AI_THRESHOLD",
                "0.7",
            ),
            ("conversation_classifier", "keywords_only"): (
                "DS_CONVERSATION_CLASSIFIER_KEYWORDS_ONLY",
                "false",
            ),
            ("conversation_classifier", "skip_threshold"): (
                "DS_CONVERSATION_CLASSIFIER_SKIP_THRESHOLD",
                "0.8",
            ),
        }

        if key_path in env_map:
            new_name, fallback = env_map[key_path]
            value = os.getenv(new_name) or fallback
            if isinstance(default, bool):
                return value.lower() == "true"
            if isinstance(default, float):
                return float(value)
            if isinstance(default, int):
                return int(value)
            return value
        return default


@dataclass
class ConversationClassifierConfig:
    """Configuration for conversation actionability classifier."""

    # Enable/disable classifier
    enabled: bool = field(
        default_factory=lambda: _get_config_value(("conversation_classifier", "enabled"), True)
    )

    # AI Classification Settings
    use_ai_classification: bool = field(
        default_factory=lambda: _get_config_value(("conversation_classifier", "use_ai"), True)
    )
    ai_confidence_threshold: float = field(
        default_factory=lambda: _get_config_value(("conversation_classifier", "ai_threshold"), 0.7)
    )

    # Performance Settings
    always_use_keywords: bool = field(
        default_factory=lambda: _get_config_value(
            ("conversation_classifier", "keywords_only"), False
        )
    )

    # Skip threshold for player_chat classification
    skip_threshold: float = field(
        default_factory=lambda: _get_config_value(
            ("conversation_classifier", "skip_threshold"), 0.8
        )
    )


@dataclass
class ClassificationResult:
    """Result of conversation classification."""

    category: Literal["actionable", "player_chat", "ambiguous"]
    confidence: float
    method: Literal["keyword", "ai", "hybrid"]


class ConversationActionabilityClassifier:
    """Classifies messages to determine if they require GM involvement."""

    def __init__(
        self,
        config: ConversationClassifierConfig | None = None,
        embedding_service=None,
    ):
        """
        Initialize the conversation classifier.

        Args:
            config: Configuration for the classifier (uses defaults if None)
            embedding_service: Optional embedding service for AI classification
        """
        self.config = config or ConversationClassifierConfig()
        self.embedding_service = embedding_service

        # Example messages for each category (used for semantic matching)
        self.category_examples = {
            "actionable": [
                "I attack the guard",
                "What's in this room?",
                "Go to the marketplace",
                "Use my bomb",
                "Check my inventory",
                "Travel to Neotopia",
                "Search the area",
                "Examine the door",
                "How much health do I have?",
                "Show me my stats",
                "Where are we?",
                "I want to open the chest",
                "Let me check the map",
                "What time is it?",
            ],
            "player_chat": [
                "What do you think we should do?",
                "I think we should go left",
                "Maybe we should rest first",
                "Should we split up?",
                "Let's decide together",
                "We could try that approach",
                "I agree with you",
                "That sounds like a good plan",
                "What's your opinion?",
                "I'm not sure about that",
                "We need to coordinate",
                "Let's discuss our options",
                "I wonder if I should take the old service hatch",
                "I wonder whether we should go left or right",
                "I'm wondering what the best approach is",
                "I'm thinking about which path to take",
                "I'm considering our options",
                "Not sure if I should do that",
                "Trying to decide what to do next",
                "What are we working on?",
                "What are we doing?",
                "What are you working on?",
                "What do we need to do?",
                "What should we do next?",
                "How are we going to handle this?",
                "Where are we going?",
                "Why are we doing this?",
            ],
        }

        # Cache for category embeddings (computed once)
        self._category_embeddings_cache: dict[str, list[float]] = {}

    def _detects_actionable_keywords(self, message: str) -> bool:
        """
        Detect if message contains actionable keywords.

        Args:
            message: The player's message

        Returns:
            True if the message likely requires GM action
        """
        message_lower = message.lower()

        # Question words
        question_words = [
            "what",
            "where",
            "when",
            "how",
            "why",
            "who",
            "which",
            "can you",
            "will you",
            "could you",
            "would you",
        ]

        # Action verbs
        action_verbs = [
            "use",
            "go",
            "travel",
            "attack",
            "search",
            "examine",
            "check",
            "show",
            "display",
            "open",
            "close",
            "take",
            "drop",
            "give",
            "move",
            "walk",
            "run",
            "jump",
            "climb",
            "enter",
            "leave",
            "look",
            "see",
            "find",
            "get",
            "grab",
            "pick",
            "put",
            "deploy",
            "activate",
            "fire",
            "shoot",
            "cast",
            "drink",
            "eat",
            "equip",
            "unequip",
            "wear",
            "remove",
            "buy",
            "sell",
            "trade",
        ]

        # Game state queries
        state_queries = [
            "check",
            "show",
            "display",
            "status",
            "health",
            "inventory",
            "stats",
            "equipment",
            "credits",
            "level",
            "exp",
            "experience",
        ]

        # Direct command patterns
        command_patterns = [
            "i want to",
            "i'll",
            "let me",
            "i'm going to",
            "i will",
            "i need to",
            "i should",
            "i must",
        ]

        # Check for question mark
        if "?" in message:
            return True

        # Check for question words
        for word in question_words:
            if word in message_lower:
                return True

        # Check for action verbs
        for verb in action_verbs:
            if verb in message_lower:
                return True

        # Check for state queries
        for query in state_queries:
            if query in message_lower:
                return True

        # Check for command patterns
        for pattern in command_patterns:
            if pattern in message_lower:
                return True

        return False

    def _detects_player_chat_keywords(self, message: str) -> bool:
        """
        Detect if message contains player-to-player chat indicators.

        Args:
            message: The player's message

        Returns:
            True if the message is likely player-to-player chat
        """
        message_lower = message.lower()

        # Conversational phrases
        conversational_phrases = [
            "what do you think",
            "i think",
            "maybe we should",
            "should we",
            "let's decide",
            "we could",
            "we should",
            "i agree",
            "i disagree",
            "that sounds",
            "what's your opinion",
            "i'm not sure",
            "we need to coordinate",
            "let's discuss",
            "what do you say",
            "do you agree",
            "your thoughts",
            "what's your take",
            "i wonder",
            "i wonder if",
            "i wonder whether",
            "i'm wondering",
            "i'm thinking",
            "i'm considering",
            "not sure if",
            "not sure whether",
            "can't decide",
            "trying to decide",
            "trying to figure out",
        ]

        # Planning/coordination phrases
        planning_phrases = [
            "let's plan",
            "we should plan",
            "coordinate",
            "strategy",
            "tactics",
            "approach",
            "method",
            "way forward",
        ]

        # Player-to-player question patterns
        # Questions directed at other players (not game state queries)
        player_question_patterns = [
            "what are we",
            "what are you",
            "what do we",
            "what do you",
            "what did we",
            "what did you",
            "what will we",
            "what will you",
            "what should we",
            "what should you",
            "what can we",
            "what can you",
            "how are we",
            "how are you",
            "how do we",
            "how do you",
            "how did we",
            "how did you",
            "where are we going",
            "where should we",
            "where do we",
            "where do you",
            "when are we",
            "when do we",
            "when should we",
            "when will we",
            "why are we",
            "why are you",
            "why do we",
            "why do you",
            "why should we",
            "why did we",
            "why did you",
        ]

        # Questions about collaborative actions (working together)
        collaborative_patterns = [
            "working on",
            "working together",
            "doing together",
            "planning to",
            "going to do",
            "trying to do",
            "decided to",
            "agreed to",
        ]

        # Check for conversational phrases
        for phrase in conversational_phrases:
            if phrase in message_lower:
                return True

        # Check for planning phrases
        for phrase in planning_phrases:
            if phrase in message_lower:
                return True

        # Check for player-to-player question patterns
        # These are questions that are likely directed at other players, not the GM
        for pattern in player_question_patterns:
            if pattern in message_lower:
                # Additional check: if it's asking about game state (inventory, health, etc.), it's actionable
                # But if it's asking about collaborative plans/actions, it's player chat
                # If it contains collaborative patterns, it's definitely player chat (check this first)
                if any(collab in message_lower for collab in collaborative_patterns):
                    return True
                
                # Game state queries that should be actionable (more specific patterns)
                game_state_patterns = [
                    "what is my",
                    "what's my",
                    "show my",
                    "check my",
                    "display my",
                    "my inventory",
                    "my health",
                    "my stats",
                    "my status",
                    "my credits",
                    "my level",
                    "my exp",
                    "my experience",
                    "my equipment",
                    "my quest",
                    "my mission",
                    "where am i",
                    "where am i located",
                    "what is my location",
                    "what's my location",
                ]
                # If it's asking about game state, it's actionable (not player chat)
                if any(pattern in message_lower for pattern in game_state_patterns):
                    return False
                
                # If it's a player-to-player question pattern and not asking about game state, it's player chat
                return True

        # Check for collaborative action patterns
        for pattern in collaborative_patterns:
            if pattern in message_lower:
                return True

        # If message is very short and doesn't have action keywords, likely chat
        if len(message.split()) <= 3 and not self._detects_actionable_keywords(message):
            return True

        return False

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

    async def _get_category_embeddings(self) -> dict[str, list[float]]:
        """
        Get or compute embeddings for category examples.

        Returns:
            Dictionary mapping category to embedding vector
        """
        if self._category_embeddings_cache:
            return self._category_embeddings_cache

        if not self.embedding_service:
            return {}

        # Compute embeddings for all category examples
        all_examples = []
        example_map = {}  # Maps index to (category, example)

        for category, examples in self.category_examples.items():
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
                    self._category_embeddings_cache[category] = avg_embedding

            logger.info(
                f"Computed category embeddings for {len(self._category_embeddings_cache)} categories"
            )
        except Exception as e:
            logger.warning(f"Failed to compute category embeddings: {e}")
            return {}

        return self._category_embeddings_cache

    async def _classify_with_ai(self, message: str) -> dict[str, float]:
        """
        Classify message using AI embeddings.

        Args:
            message: Player message to classify

        Returns:
            Dictionary mapping categories to confidence scores (0-1)
        """
        if not self.embedding_service or not self.config.use_ai_classification:
            logger.debug("AI classification disabled or embedding service unavailable")
            return {}

        try:
            # Get category embeddings
            category_embeddings = await self._get_category_embeddings()
            if not category_embeddings:
                logger.debug("No category embeddings available for AI classification")
                return {}

            # Generate embedding for message
            message_embedding = await self.embedding_service.generate(message)

            # Calculate similarity to each category
            scores = {}
            for category, category_embedding in category_embeddings.items():
                similarity = self._cosine_similarity(message_embedding, category_embedding)
                if similarity >= self.config.ai_confidence_threshold:
                    scores[category] = similarity

            if scores:
                logger.info(f"AI classification detected categories: {scores}")
            else:
                logger.debug(
                    f"AI classification: no categories above threshold ({self.config.ai_confidence_threshold})"
                )
            return scores
        except Exception as e:
            logger.warning(f"Failed to classify message with AI: {e}")
            return {}

    async def classify(self, message: str) -> ClassificationResult:
        """
        Classify a message to determine if it requires GM involvement.

        Uses hybrid approach:
        1. Keyword matching (fast path)
        2. AI classification (for validation or when keywords are ambiguous)

        Args:
            message: The player's message

        Returns:
            ClassificationResult with category, confidence, and method
        """
        if not self.config.enabled:
            # If disabled, default to actionable (process normally)
            return ClassificationResult(category="actionable", confidence=1.0, method="keyword")

        # Get keyword matching results
        actionable_keywords = self._detects_actionable_keywords(message)
        player_chat_keywords = self._detects_player_chat_keywords(message)

        # Get AI classification results (if enabled)
        ai_results = {}
        if self.config.use_ai_classification and not self.config.always_use_keywords:
            ai_results = await self._classify_with_ai(message)

        # Decision logic
        # Priority: player_chat > actionable (thinking/planning phrases override action keywords)
        if self.config.always_use_keywords:
            # Keywords only mode - check player_chat first
            if player_chat_keywords:
                return ClassificationResult(
                    category="player_chat", confidence=0.8, method="keyword"
                )
            if actionable_keywords:
                return ClassificationResult(category="actionable", confidence=0.9, method="keyword")
            return ClassificationResult(category="ambiguous", confidence=0.5, method="keyword")
        # Hybrid: Use keywords first, validate/refine with AI
        # Check player_chat first since it's more specific
        actionable_score = ai_results.get("actionable", 0.0)
        player_chat_score = ai_results.get("player_chat", 0.0)

        # If both keywords and AI agree on player_chat (priority check)
        if player_chat_keywords and player_chat_score >= self.config.ai_confidence_threshold:
            return ClassificationResult(
                category="player_chat", confidence=max(0.8, player_chat_score), method="hybrid"
            )

        # If keywords suggest player_chat (even if AI is uncertain, prioritize chat)
        if player_chat_keywords:
            # Player chat keywords are strong indicators - trust them
            if player_chat_score >= self.config.ai_confidence_threshold:
                return ClassificationResult(
                    category="player_chat", confidence=max(0.8, player_chat_score), method="hybrid"
                )
            # Keywords suggest chat but AI is uncertain - still trust keywords
            return ClassificationResult(category="player_chat", confidence=0.75, method="hybrid")

        # If both keywords and AI agree on actionable
        if actionable_keywords and actionable_score >= self.config.ai_confidence_threshold:
            return ClassificationResult(
                category="actionable", confidence=max(0.9, actionable_score), method="hybrid"
            )

        # If keywords suggest actionable but AI doesn't strongly disagree
        if actionable_keywords:
            if actionable_score < (1.0 - self.config.ai_confidence_threshold):
                # AI disagrees, but keywords are strong - still actionable
                return ClassificationResult(category="actionable", confidence=0.85, method="hybrid")
            return ClassificationResult(category="actionable", confidence=0.9, method="hybrid")

        # If AI strongly suggests actionable
        if actionable_score >= self.config.ai_confidence_threshold:
            return ClassificationResult(
                category="actionable", confidence=actionable_score, method="ai"
            )

        # If AI strongly suggests player_chat
        if player_chat_score >= self.config.ai_confidence_threshold:
            return ClassificationResult(
                category="player_chat", confidence=player_chat_score, method="ai"
            )

        # Ambiguous - default to actionable (let GM handle)
        return ClassificationResult(category="ambiguous", confidence=0.5, method="hybrid")
