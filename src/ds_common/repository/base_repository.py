import logging
from typing import Any, Generic, TypeVar

from surrealdb.data.types.record_id import RecordID

from ds_common.models.surreal_model import BaseSurrealModel
from ds_discord_bot.surreal_manager import SurrealManager

T = TypeVar("T", bound=BaseSurrealModel)


class BaseRepository(Generic[T]):
    def __init__(
        self,
        surreal_manager: SurrealManager,
        model_class: type[T],
        table_name: str | None = None,
    ):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.surreal_manager: SurrealManager = surreal_manager
        self.model_class: type[T] = model_class
        self.table_name: str = table_name or (
            model_class.model_config.get("table_name") or model_class.__name__.lower()
        )

    async def get_by_(
        self, field: str, value: Any, case_sensitive: bool = True
    ) -> T | None:
        if field not in self.model_class.model_fields.keys():
            raise ValueError(f"Field {field} not found in model {self.model_class}")

        # Quote value if it's a string, otherwise use the value as is
        if isinstance(value, str):
            value = f"'{value}'"

        query = f"SELECT * FROM {self.table_name} WHERE {field} = {value}"
        if not case_sensitive:
            query = f"SELECT * FROM {self.table_name} WHERE string::lowercase({field}) = {value}"

        self.logger.debug(f"Query: {query}")

        async with self.surreal_manager.get_db() as db:
            result = await db.query(query)
        self.logger.debug(f"Result: {result}")

        if not result:
            self.logger.debug("No result found")
            return None

        self.logger.debug(f"Result found: {result[0]}")
        return self.model_class(**result[0])

    async def get_by_id(self, id: str | RecordID) -> T | None:
        self.logger.debug(f"Getting {self.table_name} by id: {id} {type(id)}")

        if not isinstance(id, RecordID):
            id = RecordID.parse(id)

        async with self.surreal_manager.get_db() as db:
            result = await db.select(id)
        self.logger.debug(f"Result: {result}")
        if not result:
            self.logger.debug("No result found")
            return None

        self.logger.debug(f"Result found: {result}")
        return self.model_class(**result)

    async def get_all(self) -> list[T]:
        self.logger.debug(f"Getting all {self.table_name}")

        async with self.surreal_manager.get_db() as db:
            result = await db.select(self.table_name)
        self.logger.debug(f"Result: {result}")

        if not result:
            self.logger.debug("No result found")
            return []

        self.logger.debug(f"Result found: {result}")
        return [self.model_class(**record) for record in result]

    async def update(self, model: T) -> None:
        async with self.surreal_manager.get_db() as db:
            await db.update(model.id, model.model_dump(exclude={"id"}))
        self.logger.debug(f"Updated {self.table_name} {model.id} {model}")

    async def upsert(self, model: T) -> None:
        async with self.surreal_manager.get_db() as db:
            id = model.id
            data = model.model_dump(exclude={"id"})
            result = await db.upsert(id, data)

        if not result:
            self.logger.debug(f"Failed to upsert {self.table_name} {model.id} {model}")
            return

        self.logger.debug(f"Upserted {self.table_name} {model.id} {model}")
        return self.model_class(**result)

    async def delete(self, id: str | int | RecordID) -> None:
        if not isinstance(id, RecordID):
            id = RecordID.parse(id)

        async with self.surreal_manager.get_db() as db:
            await db.delete(id)
        self.logger.debug(f"Deleted {self.table_name} {id}")
