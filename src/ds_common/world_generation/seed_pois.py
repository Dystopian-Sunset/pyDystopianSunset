"""
Seed Points of Interest (POIs) for all cities.
"""

import logging
import random

from ds_common.memory.location_graph_service import LocationGraphService
from ds_common.models.location_node import LocationNode
from ds_common.repository.location_node import LocationNodeRepository
from ds_common.repository.npc import NPCRepository
from ds_common.world_generation.character_association_generator import (
    CharacterAssociationGenerator,
)
from ds_common.world_generation.edge_generator import EdgeGenerator
from ds_common.world_generation.poi_generator import POIGenerator
from ds_discord_bot.postgres_manager import PostgresManager

logger = logging.getLogger(__name__)

# City POI counts
CITY_POI_COUNTS = {
    "Neotopia": 500,
    "Driftmark": 300,
    "Skyward Nexus": 250,
    "Agrihaven": 100,
    "The Undergrid": 100,
}


async def seed_primary_cities(
    location_graph_service: LocationGraphService,
) -> dict[str, LocationNode]:
    """
    Seed primary cities as location nodes.

    Args:
        location_graph_service: Location graph service instance

    Returns:
        Dictionary mapping city names to LocationNode instances
    """
    logger.info("Seeding primary cities as location nodes...")

    cities = {
        "Neotopia": {
            "description": "The gleaming technological utopia, a city of innovation and progress where the elite thrive in luxury while the less fortunate struggle in the shadows.",
            "theme": "high-tech corporate luxury innovation",
            "atmosphere": {
                "sights": [
                    "gleaming spires",
                    "neon lights",
                    "holographic displays",
                    "luxury architecture",
                ],
                "sounds": ["electronic hums", "distant traffic", "holographic advertisements"],
                "smells": ["ozone", "synthetic materials", "clean air"],
            },
        },
        "Agrihaven": {
            "description": "An agricultural haven where rural-tech meets community values, a region of farms, processing facilities, and tight-knit communities.",
            "theme": "agricultural rural-tech community organic",
            "atmosphere": {
                "sights": [
                    "farmland",
                    "greenhouses",
                    "processing facilities",
                    "rural architecture",
                ],
                "sounds": ["farm machinery", "animal sounds", "community chatter"],
                "smells": ["earth", "crops", "fresh air", "organic materials"],
            },
        },
        "Driftmark": {
            "description": "A bustling port city where maritime trade meets transient populations, a hub of commerce and movement.",
            "theme": "maritime trade port transient",
            "atmosphere": {
                "sights": ["harbors", "ships", "warehouses", "port architecture"],
                "sounds": ["harbor activity", "ship horns", "cargo handling"],
                "smells": ["salt air", "cargo", "harbor scents"],
            },
        },
        "Skyward Nexus": {
            "description": "An elite aerial city high above the world, where exclusivity and luxury meet sky-high ambitions.",
            "theme": "aerial elite sky-high exclusive",
            "atmosphere": {
                "sights": [
                    "sky-high architecture",
                    "clouds",
                    "aerial platforms",
                    "elite structures",
                ],
                "sounds": ["wind", "distant engines", "quiet luxury"],
                "smells": ["thin air", "luxury materials", "clean atmosphere"],
            },
        },
        "The Undergrid": {
            "description": "The underground infrastructure network beneath Neotopia, home to maintenance workers and the underworld, a gritty realm of industry and shadows.",
            "theme": "industrial gritty maintenance underground",
            "atmosphere": {
                "sights": [
                    "industrial machinery",
                    "dim lighting",
                    "concrete tunnels",
                    "maintenance equipment",
                ],
                "sounds": ["mechanical grinding", "distant rumbling", "echoes"],
                "smells": ["oil", "metal", "damp", "ozone"],
            },
        },
    }

    city_nodes = {}
    for city_name, city_data in cities.items():
        location_node = await location_graph_service.create_location_node(
            location_name=city_name,
            location_type="CITY",
            description=city_data["description"],
            atmosphere=city_data["atmosphere"],
            theme=city_data["theme"],
        )
        city_nodes[city_name] = location_node
        logger.info(f"Created city location node: {city_name}")

    return city_nodes


async def seed_pois_for_city(
    location_graph_service: LocationGraphService,
    city_name: str,
    city_node: LocationNode,
    poi_count: int,
) -> list[LocationNode]:
    """
    Seed POIs for a specific city.

    Args:
        location_graph_service: Location graph service instance
        city_name: Name of the city
        city_node: City location node
        poi_count: Number of POIs to generate

    Returns:
        List of created POI location nodes
    """
    logger.info(f"Generating {poi_count} POIs for {city_name}...")

    poi_generator = POIGenerator(
        location_graph_service=location_graph_service,
        city_name=city_name,
        city_node_id=city_node.id,
        poi_count=poi_count,
    )

    pois = await poi_generator.generate_pois()
    logger.info(f"Generated {len(pois)} POIs for {city_name}")

    return pois


async def seed_all_pois(postgres_manager: PostgresManager) -> None:
    """
    Seed all POIs for all cities.

    Args:
        postgres_manager: PostgreSQL manager instance
    """
    logger.info("Starting POI seeding process...")

    location_graph_service = LocationGraphService(postgres_manager)
    npc_repository = NPCRepository(postgres_manager)
    character_association_generator = CharacterAssociationGenerator(npc_repository)
    edge_generator = EdgeGenerator(location_graph_service)

    # Seed primary cities
    city_nodes = await seed_primary_cities(location_graph_service)

    # Generate POIs for each city
    all_pois = {}
    for city_name, poi_count in CITY_POI_COUNTS.items():
        city_node = city_nodes.get(city_name)
        if not city_node:
            logger.warning(f"City node not found for {city_name}, skipping POI generation")
            continue

        pois = await seed_pois_for_city(location_graph_service, city_name, city_node, poi_count)
        all_pois[city_name] = pois

    # Generate character associations for all POIs
    logger.info("Generating character associations...")
    for city_name, pois in all_pois.items():
        # Determine POI types (simplified - would need to track this)
        poi_types = []
        for poi in pois:
            # Infer POI type from theme or name (simplified)
            if "shop" in poi.location_name.lower() or "market" in poi.location_name.lower():
                poi_types.append("COMMERCIAL")
            elif "bar" in poi.location_name.lower() or "club" in poi.location_name.lower():
                poi_types.append("ENTERTAINMENT")
            elif "housing" in poi.location_name.lower() or "residence" in poi.location_name.lower():
                poi_types.append("RESIDENTIAL")
            elif "plant" in poi.location_name.lower() or "facility" in poi.location_name.lower():
                poi_types.append("INDUSTRIAL")
            elif "plaza" in poi.location_name.lower() or "hub" in poi.location_name.lower():
                poi_types.append("PUBLIC")
            elif "hidden" in poi.location_name.lower() or "secret" in poi.location_name.lower():
                poi_types.append("SECRET")
            else:
                poi_types.append("COMMERCIAL")  # Default

        associations = await character_association_generator.generate_associations_for_pois(
            pois, poi_types
        )

        # Update location nodes with associations
        node_repository = LocationNodeRepository(postgres_manager)
        for poi in pois:
            if poi.id in associations:
                poi.character_associations = associations[poi.id]
                await node_repository.update(poi)

        logger.info(f"Generated associations for {len(pois)} POIs in {city_name}")

    # Generate edges
    logger.info("Generating location edges...")
    for city_name, pois in all_pois.items():
        city_node = city_nodes[city_name]

        # Create edges from POIs to city
        for poi in pois:
            await edge_generator.create_edge_to_city(poi, city_node)

        # Create edges between nearby POIs
        await edge_generator.create_edges_between_nearby_pois(pois, connection_probability=0.15)

        # Find transit hubs and create edges
        transit_hubs = [
            p
            for p in pois
            if "hub" in p.location_name.lower()
            or "station" in p.location_name.lower()
            or "terminal" in p.location_name.lower()
        ]
        if transit_hubs:
            major_locations = [city_node] + random.sample(pois, min(10, len(pois)))
            await edge_generator.create_transit_hub_edges(transit_hubs, major_locations)

        logger.info(f"Generated edges for {city_name}")

    logger.info("POI seeding completed!")


if __name__ == "__main__":
    import asyncio
    import os

    from dotenv import load_dotenv

    from ds_discord_bot.postgres_manager import PostgresManager

    # Load environment variables
    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    async def main():
        postgres_manager = await PostgresManager.create(
            host=os.getenv("DS_POSTGRES_HOST", "localhost"),
            port=int(os.getenv("DS_POSTGRES_PORT", "5432")),
            database=os.getenv("DS_POSTGRES_DATABASE", "game"),
            user=os.getenv("DS_POSTGRES_USER", "postgres"),
            password=os.getenv("DS_POSTGRES_PASSWORD", "postgres"),
            pool_size=int(os.getenv("DS_POSTGRES_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("DS_POSTGRES_MAX_OVERFLOW", "10")),
            echo=os.getenv("DS_POSTGRES_ECHO", "false").lower() == "true",
        )

        try:
            await seed_all_pois(postgres_manager)
        finally:
            await postgres_manager.close()

    asyncio.run(main())
