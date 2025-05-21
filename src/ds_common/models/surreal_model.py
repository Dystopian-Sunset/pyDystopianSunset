import random
import string
from abc import ABC

from pydantic import BaseModel, ConfigDict
from surrealdb import RecordID


class BaseSurrealModel(BaseModel, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True, validate_by_name=True)

    @staticmethod
    def get_id(table: str, id: str | int | RecordID) -> RecordID:
        if isinstance(id, str) and id.startswith(f"{table}:"):
            return RecordID(table, int(id.split(":")[1]))
        elif isinstance(id, int):
            return RecordID(table, id)
        elif isinstance(id, RecordID):
            return id
        else:
            return RecordID(table, str(id))

    @staticmethod
    def create_id(table: str) -> RecordID:
        return RecordID(
            table, "".join(random.choices(string.ascii_letters + string.digits, k=20))
        )