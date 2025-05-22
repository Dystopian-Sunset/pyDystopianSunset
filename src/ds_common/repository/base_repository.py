import logging
from typing import Any, Generic, TypeVar

from surrealdb import AsyncSurreal, RecordID

from ds_common.models.surreal_model import BaseSurrealModel

T = TypeVar("T", bound=BaseSurrealModel)

class BaseRepository(Generic[T]):
    def __init__(self, db: AsyncSurreal, model_class: type[T]):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.db: AsyncSurreal = db
        self.model_class: type[T] = model_class
        self.table_name: str = model_class.__name__.lower()

    async def get_by_(
        self, field: str, value: Any, case_sensitive: bool = True
    ) -> T | None:
        if field not in self.model_class.model_fields.keys():
            raise ValueError(f"Field {field} not found in model {self.model_class}")

        query = f"SELECT * FROM {self.table_name} WHERE {field} = '{value}'"
        if not case_sensitive:
            query = f"SELECT * FROM {self.table_name} WHERE string::lowercase({field}) = '{str(value).lower()}'"

        self.logger.debug(f"Query: {query}")

        result = await self.db.query(query)
        self.logger.debug(f"Result: {result}")

        if not result:
            self.logger.debug("No result found")
            return None

        self.logger.debug(f"Result found: {result[0]}")
        return self.model_class(**result[0])

    async def get_by_id(self, id: str | int | RecordID) -> T | None:
        id = BaseSurrealModel.get_id(self.table_name, id)
        result = await self.db.select(id)
        self.logger.debug(f"Result: {result}")
        if not result:
            self.logger.debug("No result found")
            return None

        self.logger.debug(f"Result found: {result}")
        return self.model_class(**result)

    async def get_all(self) -> list[T]:
        result = await self.db.select(self.table_name)
        self.logger.debug(f"Result: {result}")

        if not result:
            self.logger.debug("No result found")
            return []

        self.logger.debug(f"Result found: {result}")
        return [self.model_class(**record) for record in result]

    async def insert(self, model: T) -> None:
        await self.db.insert(self.table_name, model.model_dump())
        self.logger.debug(f"Inserted {self.table_name} {model.id} {model}")

    async def update(self, model: T) -> None:
        id = BaseSurrealModel.get_id(self.table_name, model.id)
        await self.db.update(id, model.model_dump())
        self.logger.debug(f"Updated {self.table_name} {id} {model}")

    async def upsert(self, model: T) -> None:
        id = BaseSurrealModel.get_id(self.table_name, model.id)
        await self.db.upsert(id, model.model_dump())
        self.logger.debug(f"Upserted {self.table_name} {id} {model}")

    async def delete(self, id: str | int | RecordID) -> None:
        id = BaseSurrealModel.get_id(self.table_name, id)
        await self.db.delete(id)
        self.logger.debug(f"Deleted {self.table_name} {id}")