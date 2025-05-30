from datetime import datetime, timezone

from pydantic import ConfigDict, Field

from ds_common.models.surreal_model import BaseSurrealModel


class Skill(BaseSurrealModel):
    name: str
    description: str
    created_at: Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    model_config = ConfigDict(table_name="skill")