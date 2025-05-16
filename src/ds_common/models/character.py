from datetime import datetime
from sqlmodel import Field, SQLModel


class Character(SQLModel, table=True):
    id: int = Field(primary_key=True)
    discord_id: int = Field(foreign_key="discord_user.discord_id")
    name: str
    base_stats: dict[str, int]
    created_at: datetime
    last_active: datetime