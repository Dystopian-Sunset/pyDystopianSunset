"""
Character cooldown model for tracking skill/ability/item cooldowns.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from sqlalchemy import DateTime
from sqlmodel import Field, Relationship

from ds_common.models.base_model import BaseSQLModel

if TYPE_CHECKING:
    from ds_common.models.character import Character

# Type alias for type checking only (not used in SQLModel field)
CooldownType = Literal["SKILL", "ABILITY", "ITEM"]


class CharacterCooldown(BaseSQLModel, table=True):
    """
    Character cooldown model for tracking when skills/abilities/items can be used again.

    Cooldowns use game time, not real time. The expires_at_game_time field stores
    when the cooldown expires in game time.
    """

    __tablename__ = "character_cooldowns"

    character_id: UUID = Field(
        foreign_key="characters.id", description="Character who has this cooldown"
    )
    cooldown_type: str = Field(description="Type of cooldown: SKILL, ABILITY, or ITEM")
    cooldown_name: str = Field(
        index=True,
        description="Name of the skill/ability/item (item uses instance_id if available)",
    )
    expires_at_game_time: datetime = Field(
        sa_type=DateTime(timezone=True),
        description="When this cooldown expires in game time (UTC datetime)",
    )
    duration_game_hours: float = Field(
        description="Original cooldown duration in game hours (for reference)"
    )

    # Relationships
    character: "Character" = Relationship(back_populates="cooldowns")
