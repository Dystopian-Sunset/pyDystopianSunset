"""
Repository for LocationFact model.
"""

import logging

from ds_common.models.location_fact import LocationFact
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class LocationFactRepository(BaseRepository[LocationFact]):
    """
    Repository for LocationFact model with geography and travel queries.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, LocationFact)
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def get_by_location_name(
        self, location_name: str, case_sensitive: bool = False
    ) -> LocationFact | None:
        """
        Get location facts by location name.

        Args:
            location_name: Name of the location
            case_sensitive: Whether the search should be case sensitive

        Returns:
            LocationFact instance or None
        """
        return await self.get_by_field(
            "location_name", location_name, case_sensitive=case_sensitive
        )

    async def get_all_cities(self) -> list[LocationFact]:
        """
        Get all city location facts.

        Returns:
            List of LocationFact instances with location_type="CITY"
        """
        all_facts = await self.get_all()
        return [fact for fact in all_facts if fact.location_type == "CITY"]

    async def get_direct_connections(self, location_name: str) -> list[str]:
        """
        Get locations directly connected to the given location.

        Args:
            location_name: Name of the location

        Returns:
            List of directly connected location names
        """
        fact = await self.get_by_location_name(location_name, case_sensitive=False)
        if not fact or not fact.connections:
            return []
        return fact.connections.get("direct", [])

    async def get_travel_required_connections(self, location_name: str) -> list[str]:
        """
        Get locations that require travel from the given location.

        Args:
            location_name: Name of the location

        Returns:
            List of locations requiring travel
        """
        fact = await self.get_by_location_name(location_name, case_sensitive=False)
        if not fact or not fact.connections:
            return []
        return fact.connections.get("requires_travel", [])

    async def are_locations_connected(
        self, location1: str, location2: str, allow_travel: bool = False
    ) -> bool:
        """
        Check if two locations are connected.

        Args:
            location1: First location name
            location2: Second location name
            allow_travel: If True, considers "requires_travel" as connected

        Returns:
            True if locations are connected
        """
        fact1 = await self.get_by_location_name(location1, case_sensitive=False)
        if not fact1:
            return False

        direct = fact1.connections.get("direct", []) if fact1.connections else []
        if location2 in direct:
            return True

        if allow_travel:
            travel = fact1.connections.get("requires_travel", []) if fact1.connections else []
            if location2 in travel:
                return True

        return False

    async def get_travel_requirements(self, from_location: str, to_location: str) -> dict | None:
        """
        Get travel requirements between two locations.

        Args:
            from_location: Starting location
            to_location: Destination location

        Returns:
            Travel requirements dict or None if not found
        """
        fact = await self.get_by_location_name(from_location, case_sensitive=False)
        if not fact or not fact.travel_requirements:
            return None
        return fact.travel_requirements.get(to_location)
