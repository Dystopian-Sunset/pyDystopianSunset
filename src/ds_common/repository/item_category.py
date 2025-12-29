from ds_common.models.item_category import ItemCategory
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class ItemCategoryRepository(BaseRepository[ItemCategory]):
    """
    Repository for ItemCategory model with relationship operations.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, ItemCategory)
