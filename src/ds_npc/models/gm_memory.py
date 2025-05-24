from datetime import datetime, timezone

from pydantic import Field
from surrealdb import RecordID

from ds_common.models.surreal_model import BaseSurrealModel


class GMHistory(BaseSurrealModel):
    id: RecordID = Field(
        primary_key=True,
        default_factory=lambda: BaseSurrealModel.create_id("gm_history"),
    )
    game_session_id: str
    character_name: str
    request: str
    model_messages: list[dict]
    created_at: Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )