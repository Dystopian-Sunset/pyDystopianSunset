from datetime import datetime
from sqlmodel import Field, SQLModel

class DiscordUser(SQLModel, table=True):
    id: int = Field(primary_key=True)
    global_name: str
    display_name: str
    display_avatar: str
    joined_at: datetime
    last_active: datetime
    is_active: bool