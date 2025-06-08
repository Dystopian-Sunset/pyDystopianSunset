import random
import string
from abc import ABC
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator
from pydantic.types import Annotated
from surrealdb.data.types.record_id import RecordID

from ds_common.models.record_id_annotation import RecordIDAnnotation

RecordIDType = Annotated[RecordID, RecordIDAnnotation]


class BaseSurrealModel(BaseModel, ABC):
    id: RecordIDType

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
            data["id"] = self.create_id()

        super().__init__(**data)

    @field_validator("id", mode="before", check_fields=False)
    def validate_id(cls, v) -> RecordID:
        if isinstance(v, RecordID):
            return str(v)

        raise ValueError(f"Invalid ID: {v} should be string, number or RecordID")

    @field_serializer("id", mode="plain", check_fields=False)
    def serialize_id(cls, v) -> str:
        if isinstance(v, RecordID):
            return str(v)

        if isinstance(v, str):
            if ":" in v:
                parts = v.split(":")
                if len(parts) != 2:
                    raise ValueError(
                        f"Invalid ID: {v} string format should be <table>:<id>"
                    )
                id = RecordID.parse(f"{parts[0]}:{parts[1]}")
                return str(id)
            else:
                raise ValueError(
                    f"Invalid ID: {v} string format should be <table>:<id>"
                )

        # raise ValueError(f"Invalid ID: {v} should be string or RecordID")

    @staticmethod
    def create_table_id(
        table: str, identifier: str | int | None = None
    ) -> RecordIDType:
        """Create a new RecordID for the given table"""

        if not identifier:
            identifier = "".join(
                random.choices(string.ascii_letters + string.digits, k=20)
            )

        return RecordIDType(
            table_name=table,
            identifier=identifier,
        )

    @classmethod
    def create_id(cls, identifier: str | int | None = None) -> RecordIDType:
        return cls.create_table_id(cls.model_config.get("table_name"), identifier)
