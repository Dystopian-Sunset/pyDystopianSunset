from pydantic import Field
from surrealdb import RecordID

from ds_common.models.surreal_model import BaseSurrealModel


class CharacterClass(BaseSurrealModel):
    id: RecordID = Field(primary_key=True)
    name: str
    description: str
    emoji: str