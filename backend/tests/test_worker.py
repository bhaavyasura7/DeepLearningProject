from app.services.job_queue import JobQueue
from app.worker import process_pending_jobs
from app.models.job import BackgroundJob


def test_background_job_processing(db, test_user):
    # Enqueue a preference update job
    job = JobQueue.enqueue(
        db=db,
        job_type="preference.update",
        user_id=test_user.id,
        idempotency_key=f"test_job_{test_user.id}"
    )
    assert job.status == "queued"

    # Worker processes pending jobs
    processed = process_pending_jobs(db, max_jobs=5)
    assert processed >= 1

    # Reload job and verify succeeded
    db.refresh(job)
    assert job.status == "succeeded"
    assert job.completed_at is not None
