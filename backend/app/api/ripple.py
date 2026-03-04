import csv

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.classes import _require_class_teacher
from app.core.database import get_db
from app.models.assignment import Assignment
from app.models.ripple import RippleModeration, RippleResource
from app.models.user import User
from app.schemas.ripple import RippleImportResult, RippleStats
from app.services.auth_service import get_current_user

router = APIRouter(
    prefix="/classes/{class_id}/assignments/{assignment_id}/ripple",
    tags=["ripple"],
)


def _get_assignment_or_404(class_id: int, assignment_id: int, db: Session) -> Assignment:
    assignment = db.get(Assignment, assignment_id)
    if assignment is None or assignment.class_id != class_id:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


@router.post("/import", response_model=RippleImportResult)
async def import_ripple_csv(
    class_id: int,
    assignment_id: int,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a RiPPLE resource or moderation CSV export.
    Type is auto-detected from column headers.
    Replaces any existing rows of that type for this assignment.
    """
    _require_class_teacher(class_id, current_user, db)
    assignment = _get_assignment_or_404(class_id, assignment_id, db)

    content = await file.read()
    # Try common encodings; RiPPLE exports may vary
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise HTTPException(status_code=400, detail="Could not decode CSV file — unsupported encoding")

    lines = text.splitlines()

    # Skip the first two header rows (Start Date / End Date metadata)
    if len(lines) < 3:
        raise HTTPException(status_code=400, detail="CSV file too short to parse")

    reader = csv.DictReader(lines[2:])
    rows = list(reader)
    fieldnames = reader.fieldnames or []

    # Auto-detect type
    if "Topics" in fieldnames:
        csv_type = "resource"
    elif "Topic IDs" in fieldnames:
        csv_type = "moderation"
    else:
        raise HTTPException(
            status_code=400,
            detail="Could not detect CSV type — expected 'Topics' (resource) or 'Topic IDs' (moderation) column",
        )

    if csv_type == "resource":
        db.query(RippleResource).filter(
            RippleResource.assignment_id == assignment.id
        ).delete()

        section_cols = [f for f in fieldnames if f.startswith("Section ")]
        records = []
        for row in rows:
            sections = [row[col] for col in section_cols if (row.get(col) or "").strip()]
            records.append(
                RippleResource(
                    assignment_id=assignment.id,
                    resource_id=row.get("Resource ID") or "",
                    primary_author_id=row.get("Primary Author ID") or "",
                    primary_author_name=row.get("Primary Author") or "",
                    resource_type=row.get("Resource Type") or "",
                    resource_status=row.get("Status") or "",
                    topics=row.get("Topics") or "",
                    sections=sections,
                )
            )
        db.add_all(records)
        db.commit()
        return RippleImportResult(type="resource", imported=len(records))

    else:  # moderation
        db.query(RippleModeration).filter(
            RippleModeration.assignment_id == assignment.id
        ).delete()

        rubric_cols = [f for f in fieldnames if f.startswith("Rubric ")]
        records = []
        for row in rows:
            rubric_scores = {col: row.get(col) or "" for col in rubric_cols}
            records.append(
                RippleModeration(
                    assignment_id=assignment.id,
                    resource_id=row.get("Resource ID") or "",
                    user_id=row.get("User ID") or "",
                    role=row.get("Role") or "",
                    comment=row.get("Comment") or "",
                    rubric_scores=rubric_scores,
                )
            )
        db.add_all(records)
        db.commit()
        return RippleImportResult(type="moderation", imported=len(records))


@router.get("/stats", response_model=RippleStats)
def get_ripple_stats(
    class_id: int,
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return counts of imported resource and moderation rows."""
    _require_class_teacher(class_id, current_user, db)
    assignment = _get_assignment_or_404(class_id, assignment_id, db)

    resources = (
        db.query(RippleResource)
        .filter(RippleResource.assignment_id == assignment.id)
        .count()
    )
    moderations = (
        db.query(RippleModeration)
        .filter(RippleModeration.assignment_id == assignment.id)
        .count()
    )
    return RippleStats(resources=resources, moderations=moderations)
