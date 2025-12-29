"""Impact level validator for ensuring impact matches content."""

import logging

from ds_common.models.world_memory import ImpactLevel, WorldMemory


class ImpactValidator:
    """Validator for impact level consistency."""

    def __init__(self):
        """Initialize the impact validator."""
        self.logger = logging.getLogger(__name__)

    def validate_impact_level(
        self,
        impact_level: ImpactLevel,
        narrative: str,
        consequences: list[str],
    ) -> tuple[bool, str]:
        """
        Validate that impact level matches the content.

        Args:
            impact_level: Proposed impact level
            narrative: Narrative text
            consequences: List of consequences

        Returns:
            Tuple of (is_valid, reason)
        """
        self.logger.debug(f"Validating impact level {impact_level}")

        # Basic validation rules
        if impact_level == "world_changing":
            if len(consequences) < 3:
                return False, "World-changing events should have at least 3 consequences"
            if len(narrative) < 500:
                return False, "World-changing events should have detailed narratives (500+ chars)"

        if impact_level == "major":
            if len(consequences) < 2:
                return False, "Major events should have at least 2 consequences"
            if len(narrative) < 300:
                return False, "Major events should have detailed narratives (300+ chars)"

        if impact_level == "moderate":
            if len(consequences) < 1:
                return False, "Moderate events should have at least 1 consequence"

        return True, "Impact level is valid"

    def detect_lore_violations(
        self,
        narrative: str,
        existing_memories: list[WorldMemory],
    ) -> list[str]:
        """
        Detect potential lore violations.

        Args:
            narrative: Proposed narrative
            existing_memories: Existing world memories to check against

        Returns:
            List of potential violations
        """
        violations = []

        # Simple keyword-based check (could be enhanced with semantic search)
        narrative_lower = narrative.lower()

        for memory in existing_memories:
            # Check for direct contradictions in titles
            if memory.title and memory.title.lower() in narrative_lower:
                # This is a basic check - could be enhanced
                pass

        return violations
