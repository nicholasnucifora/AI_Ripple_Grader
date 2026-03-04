"""
Standalone grading worker — run from backend/ directory:
    python worker.py

Polls the DB every POLL_INTERVAL seconds for queued grading jobs.
Stateless: on startup, resets any "running" jobs back to "queued"
so interrupted runs are automatically resumed.
"""
import logging
import time

from app.core.database import SessionLocal, engine
from app.models.grade import GradingJob
from app.services.grading_logic import grade_assignment

POLL_INTERVAL = 5  # seconds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [worker] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def reset_interrupted(db) -> None:
    """Any job left in 'running' state from a previous crash → reset to 'queued'."""
    count = (
        db.query(GradingJob)
        .filter(GradingJob.status == "running")
        .update({"status": "queued"})
    )
    if count:
        db.commit()
        logger.info("Reset %d interrupted job(s) to queued", count)


def claim_next_job(db) -> GradingJob | None:
    """Return the next queued job, using skip-locked if PostgreSQL."""
    q = db.query(GradingJob).filter(GradingJob.status == "queued").order_by(GradingJob.id)
    if engine.dialect.name == "postgresql":
        q = q.with_for_update(skip_locked=True)
    return q.first()


def main():
    db = SessionLocal()
    try:
        reset_interrupted(db)
        logger.info("Worker started — polling every %ds", POLL_INTERVAL)
        while True:
            job = claim_next_job(db)
            if job:
                logger.info("Picked up job id=%d for assignment_id=%d", job.id, job.assignment_id)
                grade_assignment(job.assignment_id, db)
            else:
                time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    finally:
        db.close()


if __name__ == "__main__":
    main()
