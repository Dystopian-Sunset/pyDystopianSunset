"""
Repository for NPC model.
"""

import logging

from ds_common.metrics.service import get_metrics_service
from ds_common.models.npc import NPC
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class NPCRepository(BaseRepository[NPC]):
    """
    Repository for NPC model.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, NPC)
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.metrics = get_metrics_service()

    async def create(self, model: NPC, session=None):
        """Create an NPC and log/metric the world state change."""
        created_npc = await super().create(model, session)
        
        # Log and record metrics for world state change
        self.logger.info(
            f"World state change: NPC created - {created_npc.name} "
            f"(ID: {created_npc.id}, Race: {created_npc.race}, "
            f"Profession: {created_npc.profession}, Level: {created_npc.level}, "
            f"Location: {created_npc.location})"
        )
        self.metrics.record_world_state_change("npc", "created")
        
        return created_npc
