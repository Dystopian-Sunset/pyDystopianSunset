"""
Character association generator for POIs.
"""

import random
from uuid import UUID

from ds_common.models.location_node import LocationNode
from ds_common.models.npc import NPC
from ds_common.repository.npc import NPCRepository

# Association types
ASSOCIATION_TYPES = [
    "OWNER_OPERATOR",  # NPC owns/runs the POI
    "RESIDENT",  # NPC lives at/near the POI
    "WORKER",  # NPC works at the POI
    "REGULAR",  # NPC frequently visits the POI
    "FACTION_MEMBER",  # NPC is associated with faction POI
]

# Association type probabilities by POI type
ASSOCIATION_PROBABILITIES = {
    "COMMERCIAL": {
        "OWNER_OPERATOR": 0.4,
        "WORKER": 0.3,
        "REGULAR": 0.2,
        "RESIDENT": 0.1,
    },
    "ENTERTAINMENT": {
        "OWNER_OPERATOR": 0.3,
        "WORKER": 0.2,
        "REGULAR": 0.4,
        "RESIDENT": 0.1,
    },
    "RESIDENTIAL": {
        "RESIDENT": 0.7,
        "WORKER": 0.2,
        "REGULAR": 0.1,
    },
    "INDUSTRIAL": {
        "WORKER": 0.8,
        "OWNER_OPERATOR": 0.1,
        "RESIDENT": 0.1,
    },
    "PUBLIC": {
        "REGULAR": 0.5,
        "WORKER": 0.3,
        "RESIDENT": 0.2,
    },
    "SECRET": {
        "FACTION_MEMBER": 0.5,
        "OWNER_OPERATOR": 0.3,
        "REGULAR": 0.2,
    },
    "FACTION": {
        "FACTION_MEMBER": 0.8,
        "OWNER_OPERATOR": 0.1,
        "WORKER": 0.1,
    },
}


class CharacterAssociationGenerator:
    """
    Generator for character associations with POIs.
    """

    def __init__(self, npc_repository: NPCRepository):
        """
        Initialize the character association generator.

        Args:
            npc_repository: NPC repository instance
        """
        self.npc_repository = npc_repository

    def _get_association_type(self, poi_type: str) -> str:
        """
        Get a random association type for a POI type.

        Args:
            poi_type: Type of POI

        Returns:
            Association type string
        """
        probabilities = ASSOCIATION_PROBABILITIES.get(poi_type, {"REGULAR": 1.0})
        types = list(probabilities.keys())
        weights = list(probabilities.values())
        return random.choices(types, weights=weights, k=1)[0]

    async def create_npc_for_poi(
        self,
        location_node: LocationNode,
        poi_type: str,
    ) -> tuple[NPC, dict]:
        """
        Create an NPC associated with a POI.

        Args:
            location_node: Location node for the POI
            poi_type: Type of POI

        Returns:
            Tuple of (created NPC, association dict)
        """
        from ds_common.name_generator import NameGenerator

        # Generate NPC name
        npc_name = NameGenerator.generate_cyberpunk_channel_name().replace("-", " ").title()

        # Get association type
        association_type = self._get_association_type(poi_type)

        # Determine profession based on association type and POI type
        professions = {
            "OWNER_OPERATOR": ["Shopkeeper", "Owner", "Manager", "Operator"],
            "WORKER": ["Worker", "Employee", "Staff", "Laborer"],
            "REGULAR": ["Regular", "Patron", "Visitor", "Customer"],
            "RESIDENT": ["Resident", "Tenant", "Local", "Inhabitant"],
            "FACTION_MEMBER": ["Member", "Agent", "Operative", "Enforcer"],
        }
        profession = random.choice(professions.get(association_type, ["Citizen"]))

        # Determine race (random for now)
        races = ["Human", "Hedgehog", "Wolf", "Fox", "Raven", "Snake", "Bear"]
        race = random.choice(races)

        # Determine background
        backgrounds = {
            "OWNER_OPERATOR": ["Business Owner", "Entrepreneur", "Merchant"],
            "WORKER": ["Worker", "Laborer", "Employee"],
            "REGULAR": ["Local", "Patron", "Regular"],
            "RESIDENT": ["Resident", "Local", "Inhabitant"],
            "FACTION_MEMBER": ["Faction Member", "Gang Member", "Operative"],
        }
        background = random.choice(backgrounds.get(association_type, ["Citizen"]))

        # Create NPC using the generate_npc class method
        npc = await NPC.generate_npc(
            name=npc_name,
            race=race,
            background=background,
            profession=profession,
            faction=None,  # Will be set if faction POI
            location=location_node.location_name,
        )

        created_npc = await self.npc_repository.create(npc)
        
        # Note: Logging and metrics are handled in NPCRepository.create()

        # Create association dict
        association = {
            "npc_id": str(created_npc.id),
            "npc_name": created_npc.name,
            "association_type": association_type,
            "poi_type": poi_type,
        }

        return created_npc, association

    async def generate_associations_for_pois(
        self, location_nodes: list[LocationNode], poi_types: list[str]
    ) -> dict[UUID, dict]:
        """
        Generate character associations for a list of POIs.

        Args:
            location_nodes: List of location nodes (POIs)
            poi_types: List of POI types corresponding to location_nodes

        Returns:
            Dictionary mapping location node IDs to association data
        """
        associations = {}

        for location_node, poi_type in zip(location_nodes, poi_types):
            # Generate 1-3 NPCs per POI (weighted toward 1)
            num_npcs = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1], k=1)[0]

            poi_associations = []
            for _ in range(num_npcs):
                npc, association = await self.create_npc_for_poi(location_node, poi_type)
                poi_associations.append(association)

            associations[location_node.id] = {
                "nearby_npcs": poi_associations,
                "factions": [],  # Will be populated if POI is faction-related
                "npc_relationships": [],  # Will be populated with proximity networks
            }

        return associations

    async def update_location_nodes_with_associations(
        self,
        location_nodes: list[LocationNode],
        associations: dict[UUID, dict],
    ) -> list[LocationNode]:
        """
        Update location nodes with character associations.

        Args:
            location_nodes: List of location nodes to update
            associations: Dictionary of associations

        Returns:
            List of updated location nodes
        """

        # This would need the repository, but for now we'll return the nodes
        # The actual update will happen in the seeding script
        updated_nodes = []
        for node in location_nodes:
            if node.id in associations:
                node.character_associations = associations[node.id]
                updated_nodes.append(node)

        return updated_nodes
