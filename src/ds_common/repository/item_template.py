from ds_common.models.item_template import ItemTemplate
from ds_common.repository.base_repository import BaseRepository
from ds_discord_bot.postgres_manager import PostgresManager


class ItemTemplateRepository(BaseRepository[ItemTemplate]):
    """
    Repository for ItemTemplate model with relationship operations.
    """

    def __init__(self, postgres_manager: PostgresManager):
        super().__init__(postgres_manager, ItemTemplate)
