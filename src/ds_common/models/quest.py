
from pydantic import Field
from surrealdb import RecordID

from ds_common.models.surreal_model import BaseSurrealModel


class Quest(BaseSurrealModel):
    id: RecordID = Field(
        primary_key=True,
        default_factory=lambda: BaseSurrealModel.create_id("quest"),
        json_schema_extra={"type": "string", "format": "table:id"},
    )
    name: str
    description: str
    tasks: list[str]
