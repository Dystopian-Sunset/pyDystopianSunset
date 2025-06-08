from typing import Any

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic_core import core_schema
from surrealdb.data.types.record_id import RecordID


class RecordIDAnnotation:
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ):
        # Accept strings and RecordID objects, output RecordID objects
        def validate(value):
            if isinstance(value, RecordID):
                return value
            return RecordID.parse(value)

        return core_schema.no_info_after_validator_function(
            validate, core_schema.str_schema()
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler: GetJsonSchemaHandler):
        # Represent as a string in JSON Schema
        return {
            "type": "string",
            "title": "RecordID",
            "examples": ["table:123", "table:⟨123⟩"],
        }
