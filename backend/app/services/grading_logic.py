"""
Pure grading logic — no HTTP, no worker mechanics, no asyncio.
Called by the worker process.
"""
import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.grade import GradeResult, GradingJob
from app.models.ripple import RippleModeration, RippleResource
from app.models.rubric import Rubric
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)


def grade_assignment(assignment_id: int, db: Session) -> None:
    job = db.query(GradingJob).filter(GradingJob.assignment_id == assignment_id).first()
    if job is None or job.status == "cancelled":
        return

    # Load rubric
    rubric_row = db.query(Rubric).filter(Rubric.assignment_id == assignment_id).first()
    if rubric_row is None:
        job.status = "error"
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.error("No rubric for assignment_id=%d", assignment_id)
        return

    rubric_dict = json.loads(rubric_row.rubric_json)

    # Load assignment for strictness
    from app.models.assignment import Assignment
    assignment = db.get(Assignment, assignment_id)
    strictness = assignment.strictness if assignment else "standard"

    # Load all resources
    resources = (
        db.query(RippleResource)
        .filter(RippleResource.assignment_id == assignment_id)
        .all()
    )

    # Already-graded resource ids (idempotency)
    done_ids = {
        row.ripple_resource_id
        for row in db.query(GradeResult.ripple_resource_id)
        .filter(
            GradeResult.assignment_id == assignment_id,
            GradeResult.status == "complete",
        )
        .all()
    }

    job.status = "running"
    job.total = len(resources)
    job.graded = len(done_ids)
    job.updated_at = datetime.now(timezone.utc)
    db.commit()

    for resource in resources:
        if resource.id in done_ids:
            continue

        # Check for cancellation
        db.refresh(job)
        if job.status == "cancelled":
            logger.info("Job cancelled for assignment_id=%d", assignment_id)
            return

        # Load matching moderations
        mods = (
            db.query(RippleModeration)
            .filter(
                RippleModeration.assignment_id == assignment_id,
                RippleModeration.resource_id == resource.resource_id,
            )
            .all()
        )
        mod_list = [{"role": m.role, "comment": m.comment} for m in mods]

        try:
            result = ai_service.grade_submission(
                sections=resource.sections,
                rubric=rubric_dict,
                moderations=mod_list,
                strictness=strictness,
            )
            grade = GradeResult(
                assignment_id=assignment_id,
                ripple_resource_id=resource.id,
                status="complete",
                criterion_grades=result["criterion_grades"],
                overall_feedback=result.get("overall_feedback", ""),
                graded_at=datetime.now(timezone.utc),
            )
            db.add(grade)
            job.graded += 1
            logger.info(
                "Graded resource_id=%s (%d/%d)",
                resource.resource_id,
                job.graded,
                job.total,
            )
        except Exception as exc:
            logger.exception("Error grading resource_id=%s: %s", resource.resource_id, exc)
            grade = GradeResult(
                assignment_id=assignment_id,
                ripple_resource_id=resource.id,
                status="error",
                criterion_grades=[],
                overall_feedback="",
                error_message=str(exc),
                graded_at=datetime.now(timezone.utc),
            )
            db.add(grade)
            job.errors += 1

        job.updated_at = datetime.now(timezone.utc)
        db.commit()

    # Final status — re-read to confirm not cancelled
    db.refresh(job)
    if job.status != "cancelled":
        job.status = "complete"
        job.completed_at = datetime.now(timezone.utc)
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(
            "Grading complete for assignment_id=%d: %d graded, %d errors",
            assignment_id,
            job.graded,
            job.errors,
        )
