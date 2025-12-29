"""
Edge generator for creating connections between locations.
"""

import random

from ds_common.memory.location_graph_service import LocationGraphService
from ds_common.models.location_node import LocationNode

# Edge type probabilities
EDGE_TYPE_PROBABILITIES = {
    "DIRECT": 0.6,  # Most connections are direct
    "REQUIRES_TRAVEL": 0.25,  # Some require travel
    "SECRET": 0.10,  # Some are secret
    "CONDITIONAL": 0.05,  # Few are conditional
}

# Travel methods by edge type
TRAVEL_METHODS = {
    "DIRECT": ["walk", "short walk", "quick walk"],
    "REQUIRES_TRAVEL": ["transport", "vehicle", "transit", "shuttle"],
    "SECRET": ["hidden path", "secret route", "back alley", "tunnel"],
    "CONDITIONAL": ["conditional access", "restricted route", "authorized path"],
}

# Travel times by edge type
TRAVEL_TIMES = {
    "DIRECT": ["a few minutes", "minutes", "a short walk"],
    "REQUIRES_TRAVEL": ["several minutes", "15-30 minutes", "an hour"],
    "SECRET": ["a few minutes", "minutes", "hidden path"],
    "CONDITIONAL": ["varies", "depends on conditions", "as needed"],
}


class EdgeGenerator:
    """
    Generator for location edges (connections/routes).
    """

    def __init__(self, location_graph_service: LocationGraphService):
        """
        Initialize the edge generator.

        Args:
            location_graph_service: Location graph service instance
        """
        self.location_graph_service = location_graph_service

    def _get_edge_type(self) -> str:
        """
        Get a random edge type based on probabilities.

        Returns:
            Edge type string
        """
        types = list(EDGE_TYPE_PROBABILITIES.keys())
        weights = list(EDGE_TYPE_PROBABILITIES.values())
        return random.choices(types, weights=weights, k=1)[0]

    def _get_travel_method(self, edge_type: str) -> str:
        """
        Get a travel method for an edge type.

        Args:
            edge_type: Type of edge

        Returns:
            Travel method string
        """
        methods = TRAVEL_METHODS.get(edge_type, ["walk"])
        return random.choice(methods)

    def _get_travel_time(self, edge_type: str) -> str:
        """
        Get a travel time for an edge type.

        Args:
            edge_type: Type of edge

        Returns:
            Travel time string
        """
        times = TRAVEL_TIMES.get(edge_type, ["a few minutes"])
        return random.choice(times)

    def _generate_narrative_description(
        self, from_location: LocationNode, to_location: LocationNode, edge_type: str
    ) -> str:
        """
        Generate a narrative description for an edge.

        Args:
            from_location: Source location
            to_location: Destination location
            edge_type: Type of edge

        Returns:
            Narrative description
        """
        templates = {
            "DIRECT": [
                f"A direct path connects {from_location.location_name} to {to_location.location_name}.",
                f"You can easily walk from {from_location.location_name} to {to_location.location_name}.",
                f"{from_location.location_name} and {to_location.location_name} are directly connected.",
            ],
            "REQUIRES_TRAVEL": [
                f"Travel from {from_location.location_name} to {to_location.location_name} requires transportation.",
                f"To reach {to_location.location_name} from {from_location.location_name}, you'll need to take transport.",
                f"A journey from {from_location.location_name} to {to_location.location_name} takes some time.",
            ],
            "SECRET": [
                f"A hidden route exists between {from_location.location_name} and {to_location.location_name}.",
                f"Those in the know can find a secret path from {from_location.location_name} to {to_location.location_name}.",
                f"An obscure connection links {from_location.location_name} and {to_location.location_name}.",
            ],
            "CONDITIONAL": [
                f"Access from {from_location.location_name} to {to_location.location_name} depends on certain conditions.",
                f"The route from {from_location.location_name} to {to_location.location_name} is not always available.",
                f"Reaching {to_location.location_name} from {from_location.location_name} requires meeting specific criteria.",
            ],
        }

        template_list = templates.get(edge_type, templates["DIRECT"])
        return random.choice(template_list)

    async def create_edge_to_city(self, poi_node: LocationNode, city_node: LocationNode) -> None:
        """
        Create an edge from a POI to its parent city.

        Args:
            poi_node: POI location node
            city_node: City location node
        """
        edge_type = "DIRECT"
        travel_method = self._get_travel_method(edge_type)
        travel_time = self._get_travel_time(edge_type)
        narrative = self._generate_narrative_description(poi_node, city_node, edge_type)

        await self.location_graph_service.create_location_edge(
            from_location_id=poi_node.id,
            to_location_id=city_node.id,
            edge_type=edge_type,
            travel_method=travel_method,
            travel_time=travel_time,
            narrative_description=narrative,
        )

    async def create_edges_between_nearby_pois(
        self, poi_nodes: list[LocationNode], connection_probability: float = 0.15
    ) -> None:
        """
        Create edges between nearby POIs.

        Args:
            poi_nodes: List of POI location nodes
            connection_probability: Probability of creating an edge between any two POIs
        """
        for i, from_poi in enumerate(poi_nodes):
            for to_poi in poi_nodes[i + 1 :]:
                if random.random() < connection_probability:
                    edge_type = self._get_edge_type()
                    travel_method = self._get_travel_method(edge_type)
                    travel_time = self._get_travel_time(edge_type)
                    narrative = self._generate_narrative_description(from_poi, to_poi, edge_type)

                    await self.location_graph_service.create_location_edge(
                        from_location_id=from_poi.id,
                        to_location_id=to_poi.id,
                        edge_type=edge_type,
                        travel_method=travel_method,
                        travel_time=travel_time,
                        narrative_description=narrative,
                    )

    async def create_transit_hub_edges(
        self, transit_hubs: list[LocationNode], major_locations: list[LocationNode]
    ) -> None:
        """
        Create edges from transit hubs to major locations.

        Args:
            transit_hubs: List of transit hub location nodes
            major_locations: List of major location nodes to connect to
        """
        for hub in transit_hubs:
            # Connect each transit hub to 3-5 major locations
            num_connections = random.randint(3, min(5, len(major_locations)))
            connected_locations = random.sample(major_locations, num_connections)

            for location in connected_locations:
                edge_type = "REQUIRES_TRAVEL"
                travel_method = "transit"
                travel_time = "15-30 minutes"
                narrative = (
                    f"Transit service connects {hub.location_name} to {location.location_name}."
                )

                await self.location_graph_service.create_location_edge(
                    from_location_id=hub.id,
                    to_location_id=location.id,
                    edge_type=edge_type,
                    travel_method=travel_method,
                    travel_time=travel_time,
                    narrative_description=narrative,
                )
