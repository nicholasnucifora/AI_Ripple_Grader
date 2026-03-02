import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import SessionLocal, engine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.env == "development":
        _init_dev_db()
    yield


def _init_dev_db() -> None:
    """
    Development convenience: create all tables and seed default mock users.
    In production, Alembic manages the schema — this function is never called.
    """
    import app.models  # noqa: F401 — ensures all models are registered on Base
    from app.core.database import Base

    Base.metadata.create_all(bind=engine)
    _seed_mock_users()


def _seed_mock_users() -> None:
    """Insert default dev credentials if the mock_users table is empty."""
    import bcrypt

    from app.models.dev_session import MockUser

    def _hash(pw: str) -> str:
        return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

    defaults = [
        {
            "username": "staff_dev",
            "password": "password",
            "payload": {
                "user": "s0000001",
                "name": "Dev Staff",
                "email": "staff@dev.example.com",
                "groups": ["uq:uqStaff"],
            },
        },
        {
            "username": "student_dev",
            "password": "password",
            "payload": {
                "user": "s0000002",
                "name": "Dev Student",
                "email": "student@dev.example.com",
                "groups": ["uq:uqStudent"],
            },
        },
    ]

    db = SessionLocal()
    try:
        if db.query(MockUser).count() == 0:
            for u in defaults:
                db.add(
                    MockUser(
                        username=u["username"],
                        hashed_password=_hash(u["password"]),
                        kvd_payload=json.dumps(u["payload"]),
                    )
                )
            db.commit()
            logger.info("Seeded %d mock dev users", len(defaults))
    finally:
        db.close()


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Ripple Grader",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS must be the outermost middleware so pre-flight requests are handled
# before any auth logic runs.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Dev-mode interceptor — NEVER registered in production.
#
# This is the sole bridge between the local session cookie and the stateless
# x-kvd-payload header that all core routes rely on.  Because it is added
# conditionally here and nowhere else, there is no code path in production
# that reads the session cookie or injects the header from client-side input.
# ---------------------------------------------------------------------------
if settings.env == "development":
    from app.middleware.kvd_interceptor import DevSessionInterceptorMiddleware

    app.add_middleware(DevSessionInterceptorMiddleware)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

from app.api.auth import router as auth_router  # noqa: E402
from app.api.classes import router as classes_router  # noqa: E402
from app.api.assignments import router as assignments_router  # noqa: E402
from app.api.submissions import router as submissions_router  # noqa: E402
from app.api.rubrics import rubric_ingest_router, rubric_crud_router  # noqa: E402

app.include_router(auth_router)
app.include_router(classes_router)
app.include_router(assignments_router)
app.include_router(submissions_router)
app.include_router(rubric_ingest_router)
app.include_router(rubric_crud_router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health")
def health_check():
    return {"status": "ok", "env": settings.env}
