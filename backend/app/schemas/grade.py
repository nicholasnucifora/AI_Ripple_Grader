from datetime import datetime

from pydantic import BaseModel


class CriterionGrade(BaseModel):
    criterion_id: str
    criterion_name: str
    level_id: str
    level_title: str
    points_awarded: float
    feedback: str


class GradingJobOut(BaseModel):
    id: int
    assignment_id: int
    status: str
    total: int
    graded: int
    errors: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class GradeResultOut(BaseModel):
    id: int
    ripple_resource_id: int
    resource_id: str
    primary_author_name: str
    status: str
    criterion_grades: list[CriterionGrade]
    overall_feedback: str
    error_message: str | None
    graded_at: datetime

    model_config = {"from_attributes": True}
