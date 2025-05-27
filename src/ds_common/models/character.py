import random
from datetime import datetime, timezone

from pydantic import Field
from surrealdb import RecordID

from ds_common.models.surreal_model import BaseSurrealModel


class Character(BaseSurrealModel):
    id: RecordID = Field(
        primary_key=True,
        default_factory=lambda: BaseSurrealModel.create_id("character"),
    )
    name: str
    level: int
    exp: int
    credits: int
    stats: dict[str, int] = Field(default_factory=dict)
    effects: dict[str, int] = Field(default_factory=dict)
    renown: int
    shadow_level: int
    created_at: datetime
    last_active: datetime

    @classmethod
    async def generate_character(
        cls,
        name: str,
    ) -> "Character":
        return cls(
            name=name,
            level=1,
            exp=0,
            credits=100,
            stats={
                "CHA": random.randint(1, 20),
                "DEX": random.randint(1, 20),
                "INT": random.randint(1, 20),
                "LUK": random.randint(1, 20),
                "PER": random.randint(1, 20),
                "STR": random.randint(1, 20),
            },
            effects={},
            renown=0,
            shadow_level=0,
            created_at=datetime.now(timezone.utc),
            last_active=datetime.now(timezone.utc),
        )