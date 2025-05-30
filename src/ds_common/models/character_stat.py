from pydantic import ConfigDict

from ds_common.models.surreal_model import BaseSurrealModel


class CharacterStat(BaseSurrealModel):
    name: str
    abbr: str
    description: str
    emoji: str
    max_value: int
    is_primary: bool
    is_mutable: bool

    model_config = ConfigDict(table_name="character_stat")
