from datetime import datetime, timezone

from discord import Member
from pydantic import Field
from surrealdb import RecordID

from ds_common.models.surreal_model import BaseSurrealModel


class Player(BaseSurrealModel):
    id: RecordID = Field(
        primary_key=True,
        default_factory=lambda: BaseSurrealModel.create_id("player"),
    )
    global_name: str
    display_name: str
    display_avatar: str | None
    joined_at: datetime
    last_active: datetime
    is_active: bool = True
    is_banned: bool = False

    @classmethod
    def from_member(
        cls, member: Member, is_active: bool = True, is_banned: bool = False
    ) -> "Player":
        return cls(
            id=RecordID("player", member.id),
            global_name=member.global_name,
            display_name=member.display_name,
            display_avatar=member.display_avatar.url,
            joined_at=datetime.now(timezone.utc),
            last_active=datetime.now(timezone.utc),
            is_active=is_active,
            is_banned=is_banned,
        )
