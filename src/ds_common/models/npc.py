import random
from datetime import datetime, timezone

from pydantic import Field
from surrealdb import RecordID

from ds_common.models.surreal_model import BaseSurrealModel


class NPC(BaseSurrealModel):
    id: RecordID = Field(
        primary_key=True,
        default_factory=lambda: BaseSurrealModel.create_id("npc"),
    )
    name: str
    race: str
    background: str
    profession: str
    faction: str | None
    location: str | None
    level: int
    credits: int
    stats: dict[str, int] = Field(default_factory=dict)
    effects: dict[str, int] = Field(default_factory=dict)

    renown: int
    shadow_level: int
    created_at: datetime
    last_active: datetime

    @classmethod
    async def generate_npc(
        cls,
        name: str,
        race: str,
        background: str,
        profession: str,
        faction: str | None,
        location: str | None,
    ) -> "NPC":
        level = random.randint(1, 100)
        credits = random.randint(1, 100) * level

        max_total_stats = 100 * (level * 1.2)

        stats = {}
        # Generate stats, with a maximum of max_stats
        for stat in ["CHA", "DEX", "INT", "LUK", "PER", "STR"]:
            stat_value = random.randint(1, (max_total_stats / 6))
            max_total_stats -= stat_value

            stats[stat] = stat_value

        return cls(
            name=name,
            race=race,
            background=background,
            profession=profession,
            faction=faction,
            location=location,
            level=level,
            credits=credits,
            stats=stats,
            effects={},
            renown=0,
            shadow_level=0,
            created_at=datetime.now(timezone.utc),
            last_active=datetime.now(timezone.utc),
        )