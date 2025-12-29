"""
Geography validator for checking location relationships and travel requirements.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ds_discord_bot.postgres_manager import PostgresManager

logger = logging.getLogger(__name__)


class GeographyValidator:
    """
    Validator for geography and location relationships.
    """

    def __init__(self, postgres_manager: "PostgresManager"):
        self.postgres_manager = postgres_manager
        self.logger = logging.getLogger(__name__)

    async def are_locations_connected(
        self, location1: str, location2: str, allow_travel: bool = False
    ) -> bool:
        """
        Check if two locations are directly connected.

        Args:
            location1: First location name
            location2: Second location name
            allow_travel: If True, considers "requires_travel" as connected

        Returns:
            True if locations are connected
        """
        from ds_common.repository.location_fact import LocationFactRepository

        fact_repo = LocationFactRepository(self.postgres_manager)
        return await fact_repo.are_locations_connected(location1, location2, allow_travel)

    async def get_travel_requirements(self, from_location: str, to_location: str) -> dict | None:
        """
        Get travel requirements between two locations.

        Args:
            from_location: Starting location
            to_location: Destination location

        Returns:
            Travel requirements dict with method, time, requirements, or None
        """
        from ds_common.repository.location_fact import LocationFactRepository

        fact_repo = LocationFactRepository(self.postgres_manager)
        return await fact_repo.get_travel_requirements(from_location, to_location)

    async def validate_city_access(
        self, current_location: str, target_city: str
    ) -> tuple[bool, str | None]:
        """
        Check if a city is accessible from the current location.

        Args:
            current_location: Current location name
            target_city: Target city name

        Returns:
            Tuple of (is_accessible, error_message)
        """
        from ds_common.repository.location_fact import LocationFactRepository

        fact_repo = LocationFactRepository(self.postgres_manager)

        # Check if target is a city
        target_fact = await fact_repo.get_by_location_name(target_city, case_sensitive=False)
        if not target_fact:
            # Unknown location
            return False, f"Unknown location: {target_city}"

        if target_fact.location_type != "CITY":
            # Not a city, so access check doesn't apply
            return True, None

        # Check if cities are the same
        current_fact = await fact_repo.get_by_location_name(current_location, case_sensitive=False)
        if current_fact and current_fact.location_type == "CITY":
            if current_location.lower() == target_city.lower():
                return True, None

        # Check if cities are connected
        is_connected = await fact_repo.are_locations_connected(
            current_location, target_city, allow_travel=True
        )

        if not is_connected:
            return (
                False,
                f"{target_city} is a separate city from {current_location}. "
                f"Proper travel is required to reach it.",
            )

        return True, None

    async def get_location_hierarchy(self, location_name: str) -> dict[str, str | None]:
        """
        Get location hierarchy (city, district, sector).

        Args:
            location_name: Location name

        Returns:
            Dictionary with city, district, sector, or None if not found
        """
        from ds_common.repository.location_fact import LocationFactRepository
        from ds_common.repository.world_region import WorldRegionRepository

        fact_repo = LocationFactRepository(self.postgres_manager)
        region_repo = WorldRegionRepository(self.postgres_manager)

        fact = await fact_repo.get_by_location_name(location_name, case_sensitive=False)
        if not fact:
            return {"city": None, "district": None, "sector": None}

        # If fact has region_id, get hierarchy from region
        if fact.region_id:
            region = await region_repo.get_by_id(fact.region_id)
            if region:
                hierarchy = {"city": None, "district": None, "sector": None}

                if region.hierarchy_level == 0:  # City
                    hierarchy["city"] = region.name
                elif region.hierarchy_level == 1:  # District
                    hierarchy["district"] = region.name
                    if region.parent_region_id:
                        parent = await region_repo.get_by_id(region.parent_region_id)
                        if parent:
                            hierarchy["city"] = parent.name
                elif region.hierarchy_level == 2:  # Sector
                    hierarchy["sector"] = region.name
                    if region.parent_region_id:
                        parent = await region_repo.get_by_id(region.parent_region_id)
                        if parent:
                            hierarchy["district"] = parent.name
                            if parent.parent_region_id:
                                grandparent = await region_repo.get_by_id(parent.parent_region_id)
                                if grandparent:
                                    hierarchy["city"] = grandparent.name

                return hierarchy

        # Fallback: use location_type from fact
        hierarchy = {"city": None, "district": None, "sector": None}
        if fact.location_type == "CITY":
            hierarchy["city"] = fact.location_name
        elif fact.location_type == "DISTRICT":
            hierarchy["district"] = fact.location_name
        elif fact.location_type == "SECTOR":
            hierarchy["sector"] = fact.location_name

        return hierarchy

    async def validate_travel(
        self, from_location: str, to_location: str, method: str | None = None
    ) -> tuple[bool, str | None]:
        """
        Validate travel between two locations.

        Args:
            from_location: Starting location
            to_location: Destination location
            method: Travel method (e.g., "jump", "walk", "teleport")

        Returns:
            Tuple of (is_valid, error_message)
        """
        from ds_common.repository.location_fact import LocationFactRepository

        fact_repo = LocationFactRepository(self.postgres_manager)

        # Check if locations exist
        from_fact = await fact_repo.get_by_location_name(from_location, case_sensitive=False)
        to_fact = await fact_repo.get_by_location_name(to_location, case_sensitive=False)

        if not from_fact:
            return False, f"Unknown starting location: {from_location}"
        if not to_fact:
            return False, f"Unknown destination location: {to_location}"

        # Check if same location
        if from_location.lower() == to_location.lower():
            return True, None

        # Check constraints
        if to_fact.constraints:
            cannot_reach_by = to_fact.constraints.get("cannot_reach_by", [])
            if method and method.lower() in [m.lower() for m in cannot_reach_by]:
                return (
                    False,
                    f"Cannot reach {to_location} by {method}. "
                    f"{to_fact.constraints.get('reason', 'This method is not valid for this location.')}",
                )

        # Check if directly connected
        is_direct = await fact_repo.are_locations_connected(
            from_location, to_location, allow_travel=False
        )
        if is_direct:
            return True, None

        # Check if travel is required
        requires_travel = await fact_repo.are_locations_connected(
            from_location, to_location, allow_travel=True
        )

        if not requires_travel:
            return (
                False,
                f"{to_location} is not accessible from {from_location}. "
                f"These locations are not connected.",
            )

        # If method is instant (jump, teleport) but travel is required, it's invalid
        instant_methods = ["jump", "teleport", "instant"]
        if method and any(m in method.lower() for m in instant_methods):
            return (
                False,
                f"Cannot reach {to_location} from {from_location} by {method}. "
                f"Proper travel is required between these locations.",
            )

        return True, None
