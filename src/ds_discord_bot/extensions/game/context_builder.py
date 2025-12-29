"""
Context builder for AI agent execution.

Builds location context, game time context, events context, and memory context.
Also manages embedding service as a singleton.
"""

import logging
from uuid import UUID

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ds_common.memory.embedding_service import EmbeddingService
    from ds_discord_bot.postgres_manager import PostgresManager


logger = logging.getLogger(__name__)


class ContextBuilder:
    """Builds context for AI agent execution."""

    _embedding_service: "EmbeddingService | None" = None

    def __init__(self, postgres_manager: "PostgresManager"):
        """
        Initialize the context builder.

        Args:
            postgres_manager: The postgres manager instance
        """
        self.postgres_manager = postgres_manager

    async def get_location_context(
        self, location_id: UUID | None
    ) -> dict[str, str | UUID | None]:
        """
        Get location context including parent locations and region information.

        Args:
            location_id: Location node ID

        Returns:
            Dictionary with location context: {
                'location_id': UUID,
                'location_name': str,
                'location_type': str,
                'parent_location_id': UUID | None,
                'parent_location_name': str | None,
                'region_name': str | None,
                'city': str | None,
                'district': str | None,
                'sector': str | None,
            }
        """
        if not location_id:
            return {
                "location_id": None,
                "location_name": None,
                "location_type": None,
                "parent_location_id": None,
                "parent_location_name": None,
                "region_name": None,
                "city": None,
                "district": None,
                "sector": None,
            }

        try:
            from ds_common.repository.location_fact import LocationFactRepository
            from ds_common.repository.location_node import LocationNodeRepository
            from ds_common.repository.world_region import WorldRegionRepository

            node_repo = LocationNodeRepository(self.postgres_manager)
            fact_repo = LocationFactRepository(self.postgres_manager)
            region_repo = WorldRegionRepository(self.postgres_manager)

            location_node = await node_repo.get_by_id(location_id)
            if not location_node:
                return {
                    "location_id": location_id,
                    "location_name": None,
                    "location_type": None,
                    "parent_location_id": None,
                    "parent_location_name": None,
                    "region_name": None,
                    "city": None,
                    "district": None,
                    "sector": None,
                }

            context = {
                "location_id": location_id,
                "location_name": location_node.location_name,
                "location_type": location_node.location_type,
                "parent_location_id": location_node.parent_location_id,
                "parent_location_name": None,
                "region_name": None,
                "city": None,
                "district": None,
                "sector": None,
            }

            # Get parent location if available
            if location_node.parent_location_id:
                parent_node = await node_repo.get_by_id(location_node.parent_location_id)
                if parent_node:
                    context["parent_location_name"] = parent_node.location_name
                    # If parent is a city, set city
                    if parent_node.location_type == "CITY":
                        context["city"] = parent_node.location_name
                    # If parent is a district, set district and try to find city
                    elif parent_node.location_type == "DISTRICT":
                        context["district"] = parent_node.location_name
                        if parent_node.parent_location_id:
                            grandparent = await node_repo.get_by_id(
                                parent_node.parent_location_id
                            )
                            if grandparent and grandparent.location_type == "CITY":
                                context["city"] = grandparent.location_name

            # Get region information from location fact if available
            if location_node.location_fact_id:
                location_fact = await fact_repo.get_by_id(location_node.location_fact_id)
                if location_fact and location_fact.region_id:
                    region = await region_repo.get_by_id(location_fact.region_id)
                    if region:
                        context["region_name"] = region.name
                        # Build hierarchy from region
                        if region.hierarchy_level == 0:  # City
                            context["city"] = region.name
                        elif region.hierarchy_level == 1:  # District
                            context["district"] = region.name
                            if region.parent_region_id:
                                parent_region = await region_repo.get_by_id(
                                    region.parent_region_id
                                )
                                if parent_region:
                                    context["city"] = parent_region.name
                        elif region.hierarchy_level == 2:  # Sector
                            context["sector"] = region.name
                            if region.parent_region_id:
                                parent_region = await region_repo.get_by_id(
                                    region.parent_region_id
                                )
                                if parent_region:
                                    context["district"] = parent_region.name
                                    if parent_region.parent_region_id:
                                        grandparent_region = await region_repo.get_by_id(
                                            parent_region.parent_region_id
                                        )
                                        if grandparent_region:
                                            context["city"] = grandparent_region.name

            # Fallback: infer from location_type if no region info
            if not context["city"] and not context["district"]:
                if location_node.location_type == "CITY":
                    context["city"] = location_node.location_name
                elif location_node.location_type == "DISTRICT":
                    context["district"] = location_node.location_name
                elif location_node.location_type == "SECTOR":
                    context["sector"] = location_node.location_name

            return context
        except Exception as e:
            logger.warning(f"Failed to get location context: {e}", exc_info=True)
            return {
                "location_id": location_id,
                "location_name": None,
                "location_type": None,
                "parent_location_id": None,
                "parent_location_name": None,
                "region_name": None,
                "city": None,
                "district": None,
                "sector": None,
            }

    def get_embedding_service(
        self, config: object, redis_db_number: int = 0
    ) -> "EmbeddingService | None":
        """
        Get or create embedding service (singleton).

        Args:
            config: Configuration object with embedding settings
            redis_db_number: Redis database number (0 for prompt analyzer, 1 for memory)

        Returns:
            EmbeddingService instance or None if not available
        """
        if self._embedding_service is not None:
            return self._embedding_service

        try:
            from openai import AsyncOpenAI

            # Get embedding configuration
            embedding_base_url = getattr(config, "ai_embedding_base_url", None)
            embedding_api_key = getattr(config, "ai_embedding_api_key", None)

            # Initialize embedding service if base_url or api_key is provided
            if embedding_base_url or embedding_api_key:
                # Build client kwargs - always include api_key (required by client library)
                # Use dummy key for local services that don't require authentication
                client_kwargs = {
                    "api_key": embedding_api_key
                    if embedding_api_key
                    else "sk-ollama-local-dummy-key-not-used"
                }
                if embedding_base_url:
                    client_kwargs["base_url"] = embedding_base_url

                openai_client = AsyncOpenAI(**client_kwargs)
                from ds_common.memory.embedding_service import EmbeddingService

                # Try to get Redis client if available (for caching)
                redis_client = self._create_redis_client(config, redis_db_number)

                # Get model and dimensions from config
                embedding_model = getattr(config, "ai_embedding_model", None)
                embedding_dimensions = getattr(config, "ai_embedding_dimensions", None)

                self._embedding_service = EmbeddingService(
                    openai_client,
                    redis_client,
                    model=embedding_model,
                    dimensions=embedding_dimensions,
                )
                return self._embedding_service
        except Exception as e:
            logger.debug(f"Embedding service not available: {e}")

        return None

    def _create_redis_client(self, config: object, db_number: int):
        """
        Create a Redis client for the specified database number.

        Args:
            config: Configuration object with redis_url
            db_number: Redis database number

        Returns:
            Redis client or None if Redis is not available
        """
        try:
            import redis.asyncio as redis

            redis_url = getattr(config, "redis_url", None)
            if not redis_url:
                return None

            # Create connection with specific database number
            return redis.from_url(redis_url, db=db_number)
        except Exception as e:
            logger.debug(f"Redis not available for db {db_number}: {e}")
            return None

