import logging
import random
import string
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
        self.table_name: str = table_name or model_class.__name__.lower()

    def create_id(self, identifier: str | int | None = None) -> RecordID:
        if identifier is None:
            identifier = "".join(
                random.choices(string.ascii_letters + string.digits, k=20)
            )

        return RecordID(
            table_name=self.table_name,
            identifier=identifier,
        )

    async def get_by_(
        self, field: str, value: Any, case_sensitive: bool = True
    ) -> T | None:
        if field not in self.model_class.model_fields.keys():
            raise ValueError(f"Field {field} not found in model {self.model_class}")

        query = f"SELECT * FROM {self.table_name} WHERE {field} = '{value}'"
        if not case_sensitive:
            query = f"SELECT * FROM {self.table_name} WHERE string::lowercase({field}) = '{str(value).lower()}'"

        self.logger.debug(f"Query: {query}")

        async with self.surreal_manager.get_db() as db:
            result = await db.query(query)
        self.logger.debug(f"Result: {result}")

        if not result:
            self.logger.debug("No result found")
            return None

        self.logger.debug(f"Result found: {result[0]}")
        return self.model_class(**result[0])

    async def get_by_id(self, id: str | int | RecordID) -> T | None:
        self.logger.debug(f"Getting {self.table_name} by id: {id} {type(id)}")

        query = f"SELECT * FROM {id} LIMIT 1"

        async with self.surreal_manager.get_db() as db:
            result = await db.query(query)
        self.logger.debug(f"Result: {result}")
        if not result:
            self.logger.debug("No result found")
            return None

        self.logger.debug(f"Result found: {result}")
        return self.model_class(**result[0])

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
            await db.upsert(model.id, model.model_dump(exclude={"id"}))
        self.logger.debug(f"Upserted {self.table_name} {model.id} {model}")

    async def delete(self, id: str | int | RecordID) -> None:
        async with self.surreal_manager.get_db() as db:
            await db.delete(id)
        self.logger.debug(f"Deleted {self.table_name} {id}")