import json

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


@router.get("/status", response_model=GradingJobOut | None)
def get_grade_status(
    class_id: int,
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_class_teacher(class_id, current_user, db)
    _get_assignment_or_404(class_id, assignment_id, db)
    return db.query(GradingJob).filter(GradingJob.assignment_id == assignment_id).first()


@router.get("/report")
def get_grade_report(
    class_id: int,
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns three analytics views over the completed grade results:
      - criterion_difficulty: criteria sorted hardest→easiest by avg % score
      - topic_breakdown: per-topic average score
      - peer_ai_agreement: AI score vs peer moderation scores per resource
    """
    _require_class_teacher(class_id, current_user, db)
    _get_assignment_or_404(class_id, assignment_id, db)

    results = (
        db.query(GradeResult)
        .filter(GradeResult.assignment_id == assignment_id, GradeResult.status == "complete")
        .all()
    )

    if not results:
        return {"criterion_difficulty": [], "topic_breakdown": [], "peer_ai_agreement": []}

    # Max points per criterion from the rubric
    rubric_row = db.query(Rubric).filter(Rubric.assignment_id == assignment_id).first()
    rubric_dict = json.loads(rubric_row.rubric_json) if rubric_row else {}
    max_by_cid = {}
    for c in rubric_dict.get("criteria", []):
        levels = c.get("levels", [])
        max_by_cid[c["id"]] = max((l["points"] for l in levels), default=0) if levels else 0

    # --- Criterion difficulty ---
    crit_data = {}
    for r in results:
        for cg in r.criterion_grades or []:
            cid = cg.get("criterion_id", "")
            if not cid:
                continue
            if cid not in crit_data:
                crit_data[cid] = {
                    "criterion_id": cid,
                    "criterion_name": cg.get("criterion_name", cid),
                    "points": [],
                    "level_counts": {},
                }
            crit_data[cid]["points"].append(cg.get("points_awarded", 0))
            lvl = cg.get("level_title", "Unknown")
            crit_data[cid]["level_counts"][lvl] = crit_data[cid]["level_counts"].get(lvl, 0) + 1

    criterion_difficulty = []
    for cid, data in crit_data.items():
        pts = data["points"]
        avg = sum(pts) / len(pts) if pts else 0
        max_pts = max_by_cid.get(cid, 0)
        pct = (avg / max_pts * 100) if max_pts > 0 else 0
        criterion_difficulty.append({
            "criterion_id": cid,
            "criterion_name": data["criterion_name"],
            "avg_points": round(avg, 2),
            "max_points": max_pts,
            "avg_pct": round(pct, 1),
            "level_distribution": data["level_counts"],
        })
    criterion_difficulty.sort(key=lambda x: x["avg_pct"])

    # --- Topic breakdown ---
    topic_data = {}
    for r in results:
        resource = db.get(RippleResource, r.ripple_resource_id)
        if not resource:
            continue
        topics_str = resource.topics or ""
        topics = [t.strip() for t in topics_str.split(",") if t.strip()] or ["(no topic)"]
        ai_total = sum(cg.get("points_awarded", 0) for cg in (r.criterion_grades or []))
        max_total = sum(max_by_cid.get(cg.get("criterion_id", ""), 0) for cg in (r.criterion_grades or []))
        for topic in topics:
            if topic not in topic_data:
                topic_data[topic] = {"scores": [], "max_scores": []}
            topic_data[topic]["scores"].append(ai_total)
            topic_data[topic]["max_scores"].append(max_total)

    topic_breakdown = []
    for topic, data in topic_data.items():
        scores = data["scores"]
        max_scores = data["max_scores"]
        avg_score = sum(scores) / len(scores) if scores else 0
        avg_max = sum(max_scores) / len(max_scores) if max_scores else 0
        avg_pct = (avg_score / avg_max * 100) if avg_max > 0 else 0
        topic_breakdown.append({
            "topic": topic,
            "count": len(scores),
            "avg_score": round(avg_score, 2),
            "avg_pct": round(avg_pct, 1),
        })
    topic_breakdown.sort(key=lambda x: x["avg_pct"])

    # --- Peer vs AI agreement ---
    peer_ai = []
    for r in results:
        resource = db.get(RippleResource, r.ripple_resource_id)
        if not resource:
            continue
        ai_score = sum(cg.get("points_awarded", 0) for cg in (r.criterion_grades or []))
        max_total = sum(max_by_cid.get(cg.get("criterion_id", ""), 0) for cg in (r.criterion_grades or []))

        mods = (
            db.query(RippleModeration)
            .filter(
                RippleModeration.assignment_id == assignment_id,
                RippleModeration.resource_id == resource.resource_id,
            )
            .all()
        )

        peer_totals = []
        for mod in mods:
            total = 0
            parsed = 0
            for v in (mod.rubric_scores or {}).values():
                try:
                    total += float(str(v))
                    parsed += 1
                except (ValueError, TypeError):
                    pass
            if parsed > 0:
                peer_totals.append(round(total, 2))

        peer_ai.append({
            "resource_id": resource.resource_id,
            "primary_author_name": resource.primary_author_name,
            "ai_score": round(ai_score, 2),
            "max_score": round(max_total, 2),
            "ai_pct": round(ai_score / max_total * 100, 1) if max_total > 0 else 0,
            "peer_scores": peer_totals,
            "peer_avg": round(sum(peer_totals) / len(peer_totals), 2) if peer_totals else None,
            "peer_count": len(mods),
        })
    peer_ai.sort(key=lambda x: x["ai_score"])

    return {
        "criterion_difficulty": criterion_difficulty,
        "topic_breakdown": topic_breakdown,
        "peer_ai_agreement": peer_ai,
    }


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
