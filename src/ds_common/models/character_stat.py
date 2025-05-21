
from pydantic import Field
from surrealdb import RecordID

from ds_common.models.surreal_model import BaseSurrealModel


class CharacterStat(BaseSurrealModel):
    id: RecordID = Field(primary_key=True)
    name: str
    abbr: str
    description: str
    emoji: str
    max_value: int
    is_primary: bool
    is_mutable: bool