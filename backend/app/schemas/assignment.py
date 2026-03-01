from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class AssignmentCreate(BaseModel):
    title: str
    description: str = ""
    marking_criteria: str = ""
    strictness: Literal["lenient", "standard", "strict"] = "standard"


class AssignmentUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    marking_criteria: str | None = None
    strictness: Literal["lenient", "standard", "strict"] | None = None


class AssignmentOut(BaseModel):
    id: int
    class_id: int
    title: str
    description: str
    marking_criteria: str
    strictness: str
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}
