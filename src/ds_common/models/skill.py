from sqlmodel import Field

from ds_common.models.base_model import BaseSQLModel


class Skill(BaseSQLModel, table=True):
    """
    Skill model
    """

    __tablename__ = "skills"

    name: str = Field(description="Skill name")
    description: str = Field(description="Skill description")
