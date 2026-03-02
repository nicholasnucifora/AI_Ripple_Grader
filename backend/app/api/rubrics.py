import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.classes import _get_member, _require_class_teacher
from app.core.database import get_db
from app.models.assignment import Assignment
from app.models.rubric import Rubric
from app.models.user import User
from app.schemas.rubric import RubricOut, RubricSave, RubricSchema
from app.services.ai_service import ai_service
from app.services.auth_service import get_current_user
from app.services.document_service import document_service

# ---------------------------------------------------------------------------
# Router 1: stateless ingest (no class/assignment context)
# ---------------------------------------------------------------------------

rubric_ingest_router = APIRouter(prefix="/rubrics", tags=["rubrics"])


@rubric_ingest_router.post("/ingest")
async def ingest_rubric(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
):
    """
    Accept a PDF, DOCX, or image upload, convert to Markdown via Docling,
    then extract a structured rubric via Claude Tool Use.
    Returns: { rubric, markdown_preview } on success, or { rubric: null, error } on failure.
    """
    file_bytes = await file.read()
    filename = file.filename or "upload.pdf"

    # Step 1: convert document to Markdown
    try:
        markdown = await document_service.extract_markdown(file_bytes, filename)
    except Exception as exc:
        return {"rubric": None, "markdown_preview": None, "error": str(exc)}

    # Step 2: extract rubric via Claude
    try:
        rubric_dict = ai_service.extract_rubric(markdown)
        rubric = RubricSchema(**rubric_dict)
        markdown_preview = ai_service.format_rubric_to_markdown(rubric_dict)
        return {"rubric": rubric.model_dump(), "markdown_preview": markdown_preview}
    except Exception as exc:
        return {"rubric": None, "markdown_preview": markdown, "error": str(exc)}


# ---------------------------------------------------------------------------
# Router 2: CRUD nested under class + assignment
# ---------------------------------------------------------------------------

rubric_crud_router = APIRouter(
    prefix="/classes/{class_id}/assignments/{assignment_id}/rubric",
    tags=["rubrics"],
)


def _get_assignment_or_404(class_id: int, assignment_id: int, db: Session) -> Assignment:
    assignment = db.get(Assignment, assignment_id)
    if assignment is None or assignment.class_id != class_id:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


@rubric_crud_router.get("", response_model=RubricOut | None)
def get_rubric(
    class_id: int,
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_member(class_id, current_user, db)
    assignment = _get_assignment_or_404(class_id, assignment_id, db)
    rubric = db.query(Rubric).filter(Rubric.assignment_id == assignment.id).first()
    if rubric is None:
        return None
    return _rubric_to_out(rubric)


@rubric_crud_router.post("", response_model=RubricOut, status_code=201)
def create_rubric(
    class_id: int,
    assignment_id: int,
    body: RubricSave,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_class_teacher(class_id, current_user, db)
    assignment = _get_assignment_or_404(class_id, assignment_id, db)

    existing = db.query(Rubric).filter(Rubric.assignment_id == assignment.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Rubric already exists; use PUT to update")

    rubric = Rubric(
        assignment_id=assignment.id,
        rubric_json=json.dumps(body.rubric.model_dump()),
        is_approved=False,
    )
    db.add(rubric)
    db.commit()
    db.refresh(rubric)
    return _rubric_to_out(rubric)


@rubric_crud_router.put("", response_model=RubricOut)
def update_rubric(
    class_id: int,
    assignment_id: int,
    body: RubricSave,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_class_teacher(class_id, current_user, db)
    assignment = _get_assignment_or_404(class_id, assignment_id, db)

    rubric = db.query(Rubric).filter(Rubric.assignment_id == assignment.id).first()
    if rubric is None:
        raise HTTPException(status_code=404, detail="No rubric found; use POST to create")

    rubric.rubric_json = json.dumps(body.rubric.model_dump())
    rubric.is_approved = True
    db.commit()
    db.refresh(rubric)
    return _rubric_to_out(rubric)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _rubric_to_out(rubric: Rubric) -> RubricOut:
    rubric_data = json.loads(rubric.rubric_json)
    return RubricOut(
        id=rubric.id,
        assignment_id=rubric.assignment_id,
        rubric=RubricSchema(**rubric_data),
        is_approved=rubric.is_approved,
        created_at=rubric.created_at,
        updated_at=rubric.updated_at,
    )
