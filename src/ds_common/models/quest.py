from pydantic import ConfigDict

from ds_common.models.surreal_model import BaseSurrealModel


class Quest(BaseSurrealModel):
    name: str
    description: str
    tasks: list[str]

    model_config = ConfigDict(table_name="quest")
