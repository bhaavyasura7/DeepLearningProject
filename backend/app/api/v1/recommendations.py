from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.movie import Movie
from app.models.recommendation import RecommendationBatch, RecommendationItem
from app.models.user import User
from app.schemas.recommendation import (
    RecommendationBatchResponse,
    RecommendationItemResponse,
    RecommendationRefreshRequest,
    RecommendationFeedbackRequest,
)
from app.schemas.job import JobResponse
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.auth_service import get_current_user
from app.services.job_queue import JobQueue

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=Optional[RecommendationBatchResponse])
def get_latest_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    batch = (
        db.query(RecommendationBatch)
        .options(joinedload(RecommendationBatch.items).joinedload(RecommendationItem.movie))
        .filter(
            RecommendationBatch.user_id == current_user.id,
            RecommendationBatch.status == "completed"
        )
        .order_by(RecommendationBatch.created_at.desc())
        .first()
    )
    if not batch:
        # If user has no batch yet, trigger onboarding generation cycle
        orchestrator = AgentOrchestrator(db)
        batch = orchestrator.execute_recommendation_cycle(
            user_id=current_user.id,
            trigger_type="onboarding"
        )
        if batch:
            batch = (
                db.query(RecommendationBatch)
                .options(joinedload(RecommendationBatch.items).joinedload(RecommendationItem.movie))
                .filter(RecommendationBatch.id == batch.id)
                .first()
            )
    return batch


@router.get("/{batch_id}", response_model=RecommendationBatchResponse)
def get_recommendation_batch_by_id(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    batch = (
        db.query(RecommendationBatch)
        .options(joinedload(RecommendationBatch.items).joinedload(RecommendationItem.movie))
        .filter(RecommendationBatch.id == batch_id)
        .first()
    )
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation batch not found")
    if batch.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return batch


@router.post("/refresh", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def refresh_recommendations(
    req: RecommendationRefreshRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Enqueue recommendation generation job asynchronously
    job = JobQueue.enqueue(
        db=db,
        job_type="recommendation.generate",
        user_id=current_user.id,
        idempotency_key=f"refresh:{current_user.id}:{req.reason}"
    )
    return job


@router.post("/{recommendation_id}/feedback", response_model=RecommendationItemResponse)
def submit_recommendation_feedback(
    recommendation_id: str,
    req: RecommendationFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item = (
        db.query(RecommendationItem)
        .join(RecommendationBatch)
        .filter(
            RecommendationItem.id == recommendation_id,
            RecommendationBatch.user_id == current_user.id
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation item not found")

    item.feedback_status = req.feedback.value
    db.commit()
    db.refresh(item)

    # Schedule preference profile update and candidate refresh based on feedback
    JobQueue.enqueue(
        db=db,
        job_type="preference.update",
        user_id=current_user.id,
        idempotency_key=f"feedback:{item.id}:{req.feedback.value}"
    )
    return item
