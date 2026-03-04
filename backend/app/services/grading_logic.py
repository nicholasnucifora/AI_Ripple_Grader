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

    rubric_row = db.query(Rubric).filter(Rubric.assignment_id == assignment_id).first()
    if rubric_row is None:
        job.status = "error"
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.error("No rubric for assignment_id=%d", assignment_id)
        return

    # Copy everything we need out of ORM objects before the first commit
    rubric_dict = json.loads(rubric_row.rubric_json)

    from app.models.assignment import Assignment
    assignment = db.get(Assignment, assignment_id)
    strictness = assignment.strictness if assignment else "standard"

    # Load only IDs — plain ints are never "expired" by SQLAlchemy
    resource_ids = [
        row[0]
        for row in db.query(RippleResource.id)
        .filter(RippleResource.assignment_id == assignment_id)
        .all()
    ]

    done_ids = {
        row[0]
        for row in db.query(GradeResult.ripple_resource_id)
        .filter(
            GradeResult.assignment_id == assignment_id,
            GradeResult.status == "complete",
        )
        .all()
    }

    job.status = "running"
    job.total = len(resource_ids)
    job.graded = len(done_ids)
    job.updated_at = datetime.now(timezone.utc)
    db.commit()

    for resource_id in resource_ids:
        if resource_id in done_ids:
            continue

        # Re-query job each iteration — avoids accessing an expired ORM object
        job = db.query(GradingJob).filter(GradingJob.assignment_id == assignment_id).first()
        if job is None or job.status == "cancelled":
            logger.info("Job cancelled for assignment_id=%d", assignment_id)
            return

        # Load resource and mods fresh, then copy data out of ORM objects
        resource = db.get(RippleResource, resource_id)
        if resource is None:
            continue

        mods = (
            db.query(RippleModeration)
            .filter(
                RippleModeration.assignment_id == assignment_id,
                RippleModeration.resource_id == resource.resource_id,
            )
            .all()
        )

        # Copy data out into plain Python values
        sections = list(resource.sections or [])
        resource_id_str = resource.resource_id
        mod_list = [{"role": m.role, "comment": m.comment} for m in mods]

        # Commit before the AI call — releases the SQLite read lock so uvicorn
        # can write freely during the (potentially long) Anthropic API call.
        db.commit()

        try:
            result = ai_service.grade_submission(
                sections=sections,
                rubric=rubric_dict,
                moderations=mod_list,
                strictness=strictness,
            )
            db.add(GradeResult(
                assignment_id=assignment_id,
                ripple_resource_id=resource_id,
                status="complete",
                criterion_grades=result["criterion_grades"],
                overall_feedback=result.get("overall_feedback", ""),
                graded_at=datetime.now(timezone.utc),
            ))
            # Atomic increment — no stale in-memory value possible
            db.query(GradingJob).filter(GradingJob.assignment_id == assignment_id).update({
                "graded": GradingJob.graded + 1,
                "updated_at": datetime.now(timezone.utc),
            })
            db.commit()
            logger.info("Graded resource_id=%s", resource_id_str)
        except Exception as exc:
            logger.exception("Error grading resource_id=%s: %s", resource_id_str, exc)
            db.rollback()
            db.add(GradeResult(
                assignment_id=assignment_id,
                ripple_resource_id=resource_id,
                status="error",
                criterion_grades=[],
                overall_feedback="",
                error_message=str(exc),
                graded_at=datetime.now(timezone.utc),
            ))
            db.query(GradingJob).filter(GradingJob.assignment_id == assignment_id).update({
                "errors": GradingJob.errors + 1,
                "updated_at": datetime.now(timezone.utc),
            })
            db.commit()

    job = db.query(GradingJob).filter(GradingJob.assignment_id == assignment_id).first()
    if job and job.status != "cancelled":
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
