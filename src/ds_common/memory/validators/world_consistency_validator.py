"""
World consistency validator for checking actions against world facts and lore.
"""

import logging
from typing import TYPE_CHECKING

from ds_common.memory.validators.action_parser import parse_action
from ds_common.memory.validators.geography_validator import GeographyValidator

if TYPE_CHECKING:
    from ds_discord_bot.postgres_manager import PostgresManager

logger = logging.getLogger(__name__)


class WorldConsistencyValidator:
    """
    Main validator for world consistency checks.
    """

    def __init__(self, postgres_manager: "PostgresManager"):
        self.postgres_manager = postgres_manager
        self.geography_validator = GeographyValidator(postgres_manager)
        self.logger = logging.getLogger(__name__)

    async def validate_action(
        self, action_text: str, current_location: str | None = None
    ) -> tuple[bool, str | None]:
        """
        Validate a player action against world facts.

        Args:
            action_text: The player's action text
            current_location: Current character location (if known)

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Parse the action
        parsed = parse_action(action_text)

        # If not a travel action, basic validation passes
        if parsed["action_type"] != "travel":
            return True, None

        # Travel actions need geography validation
        if not parsed["target"]:
            # No target specified, can't validate
            return True, None

        if not current_location:
            # No current location, can't validate travel
            self.logger.warning("Cannot validate travel action: no current location")
            return True, None

        # Validate travel
        is_valid, error_msg = await self.geography_validator.validate_travel(
            current_location, parsed["target"], parsed["method"]
        )

        return is_valid, error_msg

    async def validate_location_access(
        self, current_location: str, target_location: str
    ) -> tuple[bool, str | None]:
        """
        Check if a location is accessible from the current location.

        Args:
            current_location: Current location
            target_location: Target location

        Returns:
            Tuple of (is_accessible, error_message)
        """
        return await self.geography_validator.validate_city_access(
            current_location, target_location
        )

    async def validate_travel(
        self, from_location: str, to_location: str, method: str | None = None
    ) -> tuple[bool, str | None]:
        """
        Validate travel between locations.

        Args:
            from_location: Starting location
            to_location: Destination location
            method: Travel method

        Returns:
            Tuple of (is_valid, error_message)
        """
        return await self.geography_validator.validate_travel(from_location, to_location, method)

    async def check_geography_consistency(
        self, action_text: str, current_location: str | None = None
    ) -> tuple[bool, str | None]:
        """
        Check if action makes geographic sense.

        Args:
            action_text: Action text
            current_location: Current location

        Returns:
            Tuple of (is_consistent, error_message)
        """
        return await self.validate_action(action_text, current_location)

    async def check_lore_consistency(
        self, action_text: str, current_location: str | None = None
    ) -> tuple[bool, str | None]:
        """
        Check if action contradicts established lore.

        Args:
            action_text: Action text
            current_location: Current location

        Returns:
            Tuple of (is_consistent, error_message)
        """
        from ds_common.repository.location_fact import LocationFactRepository

        parsed = parse_action(action_text)
        fact_repo = LocationFactRepository(self.postgres_manager)

        # Check target location facts
        if parsed["target"]:
            fact = await fact_repo.get_by_location_name(parsed["target"], case_sensitive=False)
            if fact and fact.facts:
                # Check if action contradicts facts
                action_lower = action_text.lower()
                for fact_text in fact.facts:
                    fact_lower = fact_text.lower()
                    # Simple contradiction detection
                    if "cannot" in fact_lower or "not" in fact_lower:
                        # Check if action tries to do something forbidden
                        if parsed["method"]:
                            method_lower = parsed["method"].lower()
                            if method_lower in fact_lower:
                                return (
                                    False,
                                    f"This action contradicts established facts about {parsed['target']}: {fact_text}",
                                )

        return True, None

    async def get_location_facts(self, location_name: str) -> list[str]:
        """
        Get established facts about a location.

        Args:
            location_name: Location name

        Returns:
            List of fact strings
        """
        from ds_common.repository.location_fact import LocationFactRepository

        fact_repo = LocationFactRepository(self.postgres_manager)
        fact = await fact_repo.get_by_location_name(location_name, case_sensitive=False)
        if not fact:
            return []
        return fact.facts or []
