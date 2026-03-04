from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.classes import _require_class_teacher
from app.core.database import get_db
from app.models.assignment import Assignment
from app.models.grade import GradeResult, GradingJob
from app.models.ripple import RippleResource
from app.models.rubric import Rubric
from app.models.user import User
from app.schemas.grade import GradingJobOut, GradeResultOut
from app.services.auth_service import get_current_user

router = APIRouter(
    prefix="/classes/{class_id}/assignments/{assignment_id}/grade",
    tags=["grade"],
)


def _get_assignment_or_404(class_id: int, assignment_id: int, db: Session) -> Assignment:
    assignment = db.get(Assignment, assignment_id)
    if assignment is None or assignment.class_id != class_id:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


def _get_job_or_404(assignment_id: int, db: Session) -> GradingJob:
    job = db.query(GradingJob).filter(GradingJob.assignment_id == assignment_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="No grading job found for this assignment")
    return job


@router.post("/start", response_model=GradingJobOut, status_code=201)
def start_grading(
    class_id: int,
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_class_teacher(class_id, current_user, db)
    _get_assignment_or_404(class_id, assignment_id, db)

    existing = db.query(GradingJob).filter(GradingJob.assignment_id == assignment_id).first()
    if existing is not None:
        raise HTTPException(status_code=400, detail="Delete existing grading first")

    resource_count = (
        db.query(RippleResource)
        .filter(RippleResource.assignment_id == assignment_id)
        .count()
    )
    if resource_count == 0:
        raise HTTPException(status_code=400, detail="No resources imported yet")

    rubric = db.query(Rubric).filter(Rubric.assignment_id == assignment_id).first()
    if rubric is None:
        raise HTTPException(status_code=400, detail="No rubric defined for this assignment")

    job = GradingJob(assignment_id=assignment_id, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.post("/cancel", response_model=GradingJobOut)
def cancel_grading(
    class_id: int,
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_class_teacher(class_id, current_user, db)
    _get_assignment_or_404(class_id, assignment_id, db)

    job = _get_job_or_404(assignment_id, db)
    job.status = "cancelled"
    db.commit()
    db.refresh(job)
    return job


@router.delete("/")
def delete_grading(
    class_id: int,
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_class_teacher(class_id, current_user, db)
    _get_assignment_or_404(class_id, assignment_id, db)

    job = _get_job_or_404(assignment_id, db)
    if job.status == "running":
        raise HTTPException(status_code=400, detail="Cancel grading before deleting")

    db.query(GradeResult).filter(GradeResult.assignment_id == assignment_id).delete()
    db.delete(job)
    db.commit()
    return Response(status_code=204)


@router.get("/status", response_model=GradingJobOut)
def get_grade_status(
    class_id: int,
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_class_teacher(class_id, current_user, db)
    _get_assignment_or_404(class_id, assignment_id, db)
    return _get_job_or_404(assignment_id, db)


@router.get("/results", response_model=list[GradeResultOut])
def get_grade_results(
    class_id: int,
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_class_teacher(class_id, current_user, db)
    _get_assignment_or_404(class_id, assignment_id, db)

    rows = (
        db.query(GradeResult)
        .filter(GradeResult.assignment_id == assignment_id)
        .order_by(GradeResult.graded_at)
        .all()
    )

    out = []
    for r in rows:
        resource = db.get(RippleResource, r.ripple_resource_id)
        out.append(
            GradeResultOut(
                id=r.id,
                ripple_resource_id=r.ripple_resource_id,
                resource_id=resource.resource_id if resource else "",
                primary_author_name=resource.primary_author_name if resource else "",
                status=r.status,
                criterion_grades=r.criterion_grades,
                overall_feedback=r.overall_feedback,
                error_message=r.error_message,
                graded_at=r.graded_at,
            )
        )
    return out
