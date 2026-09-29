import logging
import time
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.job import BackgroundJob
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.job_queue import JobQueue
from app.services.preference_service import PreferenceService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("worker")


def process_single_job(db: Session, job: BackgroundJob) -> bool:
    """Processes a single background job idempotently."""
    logger.info(f"Processing job {job.id} (type: {job.job_type}, user: {job.user_id})")
    JobQueue.mark_started(db, job)

    try:
        if job.job_type == "preference.update":
            if job.user_id:
                PreferenceService.update_preference_profile(db, job.user_id)
            JobQueue.mark_succeeded(db, job)
            return True

        elif job.job_type == "recommendation.generate":
            if job.user_id:
                orchestrator = AgentOrchestrator(db)
                orchestrator.execute_recommendation_cycle(
                    user_id=job.user_id,
                    trigger_type="interaction"
                )
            JobQueue.mark_succeeded(db, job)
            return True

        else:
            logger.warning(f"Unknown job type: {job.job_type}")
            JobQueue.mark_succeeded(db, job)
            return True

    except Exception as exc:
        logger.error(f"Error processing job {job.id}: {exc}", exc_info=True)
        JobQueue.mark_failed(db, job, error_msg=str(exc), can_retry=True)
        return False


def process_pending_jobs(db: Session, max_jobs: int = 10) -> int:
    """Processes up to max_jobs queued jobs."""
    jobs = (
        db.query(BackgroundJob)
        .filter(
            BackgroundJob.status.in_(["queued", "retry_wait"]),
            BackgroundJob.scheduled_at <= datetime.utcnow()
        )
        .order_by(BackgroundJob.scheduled_at.asc())
        .limit(max_jobs)
        .all()
    )

    processed_count = 0
    for job in jobs:
        process_single_job(db, job)
        processed_count += 1

    return processed_count


def run_worker_loop(interval_seconds: float = 2.0):
    """Continuous worker daemon loop."""
    logger.info("Starting background worker daemon...")
    while True:
        db = SessionLocal()
        try:
            count = process_pending_jobs(db, max_jobs=20)
            if count > 0:
                logger.info(f"Worker processed {count} jobs.")
        except Exception as e:
            logger.error(f"Worker error in loop: {e}", exc_info=True)
        finally:
            db.close()

        time.sleep(interval_seconds)


if __name__ == "__main__":
    run_worker_loop()
