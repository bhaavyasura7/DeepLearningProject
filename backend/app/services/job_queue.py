import logging
import uuid
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from sqlalchemy.orm import Session
from app.models.job import BackgroundJob

logger = logging.getLogger("job_queue")


class JobQueue:
    """Manages idempotent background jobs persisted in the database."""

    @staticmethod
    def enqueue(
        db: Session,
        job_type: str,
        user_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> BackgroundJob:
        if not idempotency_key:
            idempotency_key = f"{job_type}:{user_id or 'global'}:{datetime.utcnow().timestamp()}"

        # Check existing job with this idempotency key
        existing = db.query(BackgroundJob).filter(BackgroundJob.idempotency_key == idempotency_key).first()
        if existing:
            logger.info(f"Job with key {idempotency_key} already exists (status: {existing.status})")
            return existing

        job = BackgroundJob(
            id=str(uuid.uuid4()),
            job_type=job_type,
            user_id=user_id,
            idempotency_key=idempotency_key,
            status="queued",
            attempts=0,
            scheduled_at=datetime.utcnow(),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        logger.info(f"Enqueued job {job.id} of type {job.job_type} for user {user_id}")
        return job

    @staticmethod
    def get_job(db: Session, job_id: str) -> Optional[BackgroundJob]:
        return db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()

    @staticmethod
    def mark_started(db: Session, job: BackgroundJob):
        job.status = "running"
        job.started_at = datetime.utcnow()
        job.attempts += 1
        db.commit()

    @staticmethod
    def mark_succeeded(db: Session, job: BackgroundJob):
        job.status = "succeeded"
        job.completed_at = datetime.utcnow()
        job.last_error = None
        db.commit()

    @staticmethod
    def mark_failed(db: Session, job: BackgroundJob, error_msg: str, can_retry: bool = False):
        job.last_error = error_msg[:1000]
        if can_retry and job.attempts < 3:
            job.status = "retry_wait"
        else:
            job.status = "failed"
            job.completed_at = datetime.utcnow()
        db.commit()
