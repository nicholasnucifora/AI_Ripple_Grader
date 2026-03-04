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


def reset_interrupted() -> None:
    """Any job left in 'running' state from a previous crash → reset to 'queued'."""
    db = SessionLocal()
    try:
        count = (
            db.query(GradingJob)
            .filter(GradingJob.status == "running")
            .update({"status": "queued"})
        )
        if count:
            db.commit()
            logger.info("Reset %d interrupted job(s) to queued", count)
    finally:
        db.close()


def claim_next_job() -> int | None:
    """Return the assignment_id of the next queued job, or None. Closes session immediately."""
    db = SessionLocal()
    try:
        q = db.query(GradingJob).filter(GradingJob.status == "queued").order_by(GradingJob.id)
        if engine.dialect.name == "postgresql":
            q = q.with_for_update(skip_locked=True)
        job = q.first()
        return job.assignment_id if job else None
    finally:
        db.close()


def main():
    reset_interrupted()
    logger.info("Worker started — polling every %ds", POLL_INTERVAL)
    try:
        while True:
            assignment_id = claim_next_job()
            if assignment_id is not None:
                logger.info("Picked up job for assignment_id=%d", assignment_id)
                db = SessionLocal()
                try:
                    grade_assignment(assignment_id, db)
                except Exception:
                    logger.exception("Unhandled error grading assignment_id=%d", assignment_id)
                    db.rollback()
                finally:
                    db.close()
            else:
                time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")


if __name__ == "__main__":
    main()
