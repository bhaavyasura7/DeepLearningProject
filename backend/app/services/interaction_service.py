import uuid
from datetime import datetime
from typing import Optional, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.interaction import UserInteraction
from app.models.movie import Movie
from app.schemas.interaction import InteractionCreate
from app.services.job_queue import JobQueue
from app.services.preference_service import PreferenceService


class InteractionService:
    @staticmethod
    def record_interaction(
        db: Session,
        user_id: str,
        data: InteractionCreate
    ) -> Tuple[UserInteraction, bool]:
        """Records a user interaction with idempotency protection.
        
        Returns (interaction, is_created).
        """
        # 1. Check idempotency
        if data.idempotency_key:
            existing = (
                db.query(UserInteraction)
                .filter(UserInteraction.idempotency_key == data.idempotency_key)
                .first()
            )
            if existing:
                if existing.user_id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Idempotency key already used by another record"
                    )
                return existing, False

        # 2. Check movie exists
        movie = db.query(Movie).filter(Movie.id == data.movie_id).first()
        if not movie:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with id {data.movie_id} not found"
            )

        # 3. Create interaction
        interaction = UserInteraction(
            id=str(uuid.uuid4()),
            user_id=user_id,
            movie_id=data.movie_id,
            interaction_type=data.interaction_type.value,
            rating=data.rating,
            occurred_at=data.occurred_at or datetime.utcnow(),
            source=data.source or "web",
            idempotency_key=data.idempotency_key,
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)

        # 4. Enqueue background preference update job
        JobQueue.enqueue(
            db=db,
            job_type="preference.update",
            user_id=user_id,
            idempotency_key=f"pref_update:{user_id}:{interaction.id}"
        )

        # 5. Enqueue background recommendation check / generate job
        JobQueue.enqueue(
            db=db,
            job_type="recommendation.generate",
            user_id=user_id,
            idempotency_key=f"rec_gen:{user_id}:{interaction.id}"
        )

        return interaction, True

    @staticmethod
    def get_user_interactions(
        db: Session,
        user_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[UserInteraction], int]:
        if page < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page must be >= 1")
        if page_size < 1 or page_size > 100:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page size must be between 1 and 100")

        query = db.query(UserInteraction).filter(UserInteraction.user_id == user_id)
        total = query.count()
        items = (
            query.order_by(UserInteraction.occurred_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    @staticmethod
    def delete_interaction(db: Session, user_id: str, interaction_id: str) -> bool:
        interaction = (
            db.query(UserInteraction)
            .filter(UserInteraction.id == interaction_id)
            .first()
        )
        if not interaction:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interaction not found")
        if interaction.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        db.delete(interaction)
        db.commit()

        # Recompute preference profile after deletion
        PreferenceService.update_preference_profile(db, user_id)
        return True
