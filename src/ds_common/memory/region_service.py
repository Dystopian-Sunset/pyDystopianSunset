import logging
from uuid import UUID

from ds_common.models.world_event import WorldEvent
from ds_common.models.world_item import WorldItem
from ds_common.models.world_region import WorldRegion
from ds_common.repository.world_event import WorldEventRepository
from ds_common.repository.world_item import WorldItemRepository
from ds_common.repository.world_region import WorldRegionRepository
from ds_discord_bot.postgres_manager import PostgresManager


class RegionService:
    """
    Service for managing world regions, hierarchical relationships, and regional filtering.
    """

    def __init__(self, postgres_manager: PostgresManager):
        self.postgres_manager = postgres_manager
        self.region_repo = WorldRegionRepository(postgres_manager)
        self.event_repo = WorldEventRepository(postgres_manager)
        self.item_repo = WorldItemRepository(postgres_manager)
        self.logger = logging.getLogger(__name__)

    async def get_events_for_region(self, region_id: UUID) -> list[WorldEvent]:
        """
        Get all active events in a region.

        Args:
            region_id: Region ID

        Returns:
            List of WorldEvent instances
        """
        region = await self.region_repo.get_by_id(region_id)
        if not region:
            return []

        active_events = await self.event_repo.get_by_status("ACTIVE")
        region_events = []

        for event in active_events:
            if event.regional_scope:
                # Check if region matches
                locations = event.regional_scope.get("locations", [])
                if region.name in locations or str(region_id) in locations:
                    region_events.append(event)

        return region_events

    async def get_items_for_region(self, region_id: UUID) -> list[WorldItem]:
        """
        Get all available items in a region.

        Args:
            region_id: Region ID

        Returns:
            List of WorldItem instances
        """
        region = await self.region_repo.get_by_id(region_id)
        if not region:
            return []

        available_items = await self.item_repo.get_available()
        region_items = []

        for item in available_items:
            if item.regional_availability:
                regions = item.regional_availability.get("regions", [])
                locations = item.regional_availability.get("locations", [])

                if (
                    region.name in regions
                    or str(region_id) in regions
                    or any(loc in region.locations for loc in locations)
                ):
                    region_items.append(item)

        return region_items

    async def is_character_in_region(self, character_location: str, region_id: UUID) -> bool:
        """
        Check if a character is in a specific region based on location string.

        Args:
            character_location: Character's location string
            region_id: Region ID to check

        Returns:
            True if character is in region, False otherwise
        """
        region = await self.region_repo.get_by_id(region_id)
        if not region:
            return False

        # Check if location string matches region locations
        if character_location in region.locations:
            return True

        # Check hierarchical regions
        if region.parent_region_id:
            parent = await self.region_repo.get_by_id(region.parent_region_id)
            if parent and character_location in parent.locations:
                return True

        return False

    async def get_regional_variations(self, region_id: UUID, base_data: dict) -> dict:
        """
        Get regional variations for data based on region.

        Args:
            region_id: Region ID
            base_data: Base data dictionary

        Returns:
            Regional variation dict
        """
        region = await self.region_repo.get_by_id(region_id)
        if not region or not region.regional_variations:
            return base_data

        # Merge regional variations with base data
        variations = region.regional_variations.copy()
        variations.update(base_data)
        return variations

    async def get_hierarchical_regions(self, region_id: UUID) -> list[WorldRegion]:
        """
        Get all regions in the hierarchy (parent and children).

        Args:
            region_id: Region ID

        Returns:
            List of WorldRegion instances (parent, self, children)
        """
        region = await self.region_repo.get_by_id(region_id)
        if not region:
            return []

        regions = [region]

        # Get parent
        if region.parent_region_id:
            parent = await self.region_repo.get_by_id(region.parent_region_id)
            if parent:
                regions.insert(0, parent)

        # Get children
        children = await self.region_repo.get_by_parent(region_id)
        regions.extend(children)

        return regions

    async def get_faction_territories(self, faction: str) -> list[WorldRegion]:
        """
        Get all regions controlled by a faction.

        Args:
            faction: Faction name

        Returns:
            List of WorldRegion instances
        """
        return await self.region_repo.get_by_faction(faction)
