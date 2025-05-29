import random
import string
from abc import ABC

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from surrealdb.data.types.record_id import RecordID


class BaseSurrealModel(BaseModel, ABC):
    id: str = Field(primary_key=True)
    model_config = ConfigDict(arbitrary_types_allowed=True, validate_by_name=True)

    @field_serializer("id", mode="plain", check_fields=False)
    @classmethod
    def serialize_id(cls, v):
        if isinstance(v, RecordID):
            return f"{v.table_name}:{v.id}"
        return v

    @field_validator("id", mode="before", check_fields=False)
    @classmethod
    def validate_id(cls, v):
        if isinstance(v, str):
            if ":" in v:
                return RecordID(
                    table_name=v.split(":")[0], identifier=int(v.split(":")[1])
                )
            else:
                raise ValueError(
                    f"Invalid ID: {v} string format should be <table>:<id>"
                )
        if isinstance(v, RecordID):
            return v

        raise ValueError(f"Invalid ID: {v} should be string or RecordID")

    @staticmethod
    def get_id(table: str, id: str | int | RecordID) -> RecordID:
        if isinstance(id, str) and id.startswith(f"{table}:"):
            return RecordID(table_name=table, identifier=int(id.split(":")[1]))
        elif isinstance(id, int):
            return RecordID(table_name=table, identifier=id)
        elif isinstance(id, RecordID):
            return id
        else:
            raise ValueError(f"Invalid ID: {id}")

    @staticmethod
    def create_id(table: str) -> RecordID:
        return RecordID(
            table_name=table,
            identifier="".join(
                random.choices(string.ascii_letters + string.digits, k=20)
            ),
        )
