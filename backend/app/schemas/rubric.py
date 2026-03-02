from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RubricLevel(BaseModel):
    id: str
    title: str
    points: float
    description: str


class RubricCriterion(BaseModel):
    id: str
    name: str
    weight_percentage: float
    levels: list[RubricLevel]


class RubricSchema(BaseModel):
    title: str
    criteria: list[RubricCriterion]


class RubricSave(BaseModel):
    rubric: RubricSchema


class RubricOut(BaseModel):
    id: int
    assignment_id: int
    rubric: RubricSchema
    is_approved: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}
