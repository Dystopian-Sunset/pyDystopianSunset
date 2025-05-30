import random
import string
from abc import ABC
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from surrealdb.data.types.record_id import RecordID


class BaseSurrealModel(BaseModel, ABC):
    id: str = Field(primary_key=True)
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_by_name=True,  # Add JSON schema extra for better documentation
        json_schema_extra={
            "properties": {
                "id": {
                    "type": "string",
                    "pattern": "^[a-zA-Z_][a-zA-Z0-9_]*:[a-zA-Z0-9_]+$",
                    "examples": ["user:123", "post:abc123"],
                }
            }
        },
    )

    def __init__(self, **data: Any) -> None:
        if "id" not in data:
            data["id"] = self.create_id(self.model_config.get("table_name"))

        super().__init__(**data)

    @field_serializer("id", mode="plain", check_fields=False)
    @classmethod
    def serialize_id(cls, v) -> str:
        if isinstance(v, RecordID):
            return f"{v.table_name}:{v.id}"
        return v

    @field_validator("id", mode="before", check_fields=False)
    @classmethod
    def validate_id(cls, v) -> str:
        if isinstance(v, str):
            if ":" in v:
                parts = v.split(":")
                if len(parts) != 2:
                    raise ValueError(
                        f"Invalid ID: {v} string format should be <table>:<id>"
                    )
                return f"{parts[0]}:{parts[1]}"
            else:
                raise ValueError(
                    f"Invalid ID: {v} string format should be <table>:<id>"
                )
        if isinstance(v, RecordID):
            return f"{v}"

        raise ValueError(f"Invalid ID: {v} should be string or RecordID")

    @staticmethod
    def get_id(table: str, id: str | int | RecordID) -> RecordID:
        if isinstance(id, str):
            if id.startswith(f"{table}:"):
                identifier = id.split(":", 1)[1]
                return RecordID(table_name=table, identifier=identifier)
            else:
                return RecordID(table_name=table, identifier=id)
        elif isinstance(id, int):
            return RecordID(table_name=table, identifier=id)
        elif isinstance(id, RecordID):
            return id
        else:
            raise ValueError(f"Invalid ID: {id}")

    @staticmethod
    def create_table_id(table: str, identifier: str | int | None = None) -> RecordID:
        """Create a new RecordID for the given table"""

        if identifier is None:
            identifier = "".join(
                random.choices(string.ascii_letters + string.digits, k=20)
            )

        return RecordID(
            table_name=table,
            identifier=identifier,
        )

    @classmethod
    def create_id(cls, identifier: str | int | None = None) -> RecordID:
        return cls.create_table_id(cls.model_config.get("table_name"), identifier)

    def get_record_id(self) -> RecordID:
        """Convert the string ID back to RecordID when needed"""

        if ":" not in self.id:
            raise ValueError(f"Invalid ID: {self.id}")

        return RecordID.parse(self.id)
