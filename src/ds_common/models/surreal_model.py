import random
import string
from abc import ABC

from pydantic import BaseModel, ConfigDict, field_validator
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
            raise ValueError(f"Invalid ID: {id}")

    @staticmethod
    def create_id(table: str) -> RecordID:
        return RecordID(
            table, "".join(random.choices(string.ascii_letters + string.digits, k=20))
        )

    @field_validator("id", mode="before", check_fields=False)
    @classmethod
    def validate_id(cls, v: str | RecordID) -> RecordID:
        # print(f"### Validating {cls.__name__}.id with value: {v} ({type(v)})")
        if isinstance(v, str) and ":" in v:
            return RecordID(v.split(":")[0], int(v.split(":")[1]))
        elif isinstance(v, RecordID):
            return v
        else:
            raise ValueError(f"Invalid ID: {v}")