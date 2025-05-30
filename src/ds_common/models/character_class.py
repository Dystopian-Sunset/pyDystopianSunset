from pydantic import ConfigDict

from ds_common.models.surreal_model import BaseSurrealModel


class CharacterClass(BaseSurrealModel):
    """
    Character class model
    """
    name: str
    description: str
    emoji: str

    model_config = ConfigDict(table_name="character_class")
