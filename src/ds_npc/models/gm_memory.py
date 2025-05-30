from datetime import datetime, timezone

from pydantic import ConfigDict, Field

from ds_common.models.surreal_model import BaseSurrealModel


class GMHistory(BaseSurrealModel):
    game_session_id: str
    character_name: str
    request: str
    model_messages: list[dict]
    created_at: Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    model_config = ConfigDict(table_name="gm_history")