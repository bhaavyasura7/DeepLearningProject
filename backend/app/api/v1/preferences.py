from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.interaction import UserInteraction
from app.models.user import User
from app.schemas.preference import PreferenceResponse, ProfileResetResponse
from app.services.auth_service import get_current_user
from app.services.preference_service import PreferenceService

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("", response_model=PreferenceResponse)
def get_user_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = PreferenceService.get_latest_profile(db, current_user.id)
    if not profile:
        profile = PreferenceService.update_preference_profile(db, current_user.id)

    total_count = db.query(UserInteraction).filter(UserInteraction.user_id == current_user.id).count()
    # Recent count: interactions in last 30 days
    recent_count = (
        db.query(UserInteraction)
        .filter(
            UserInteraction.user_id == current_user.id,
            UserInteraction.occurred_at >= datetime.utcnow()
        )
        .count()
    )

    return PreferenceResponse(
        user_id=current_user.id,
        profile_version=profile.profile_version,
        algorithm_version=profile.algorithm_version,
        computed_at=profile.computed_at,
        long_term_preferences=profile.long_term_preferences_json or {},
        short_term_preferences=profile.short_term_preferences_json or {},
        recent_interactions_count=recent_count,
        total_interactions_count=total_count
    )


@router.post("/reset", response_model=ProfileResetResponse)
def reset_user_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    reset_prof = PreferenceService.reset_profile(db, current_user.id)
    return ProfileResetResponse(
        message="Preference profile reset successfully",
        user_id=current_user.id,
        profile_version=reset_prof.profile_version,
        reset_at=reset_prof.computed_at
    )
