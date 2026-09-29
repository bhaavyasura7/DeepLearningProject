from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserSettings
from app.schemas.auth import UserSettingsResponse
from app.schemas.settings import UserSettingsUpdate
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=UserSettingsResponse)
def get_user_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    if not settings:
        settings = UserSettings(
            user_id=current_user.id,
            recommendations_enabled=True,
            notifications_enabled=True,
            refresh_frequency="event",
            notification_cooldown=30
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.patch("", response_model=UserSettingsResponse)
def update_user_settings(
    req: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)

    if req.recommendations_enabled is not None:
        settings.recommendations_enabled = req.recommendations_enabled
    if req.notifications_enabled is not None:
        settings.notifications_enabled = req.notifications_enabled
    if req.refresh_frequency is not None:
        settings.refresh_frequency = req.refresh_frequency
    if req.notification_cooldown is not None:
        settings.notification_cooldown = req.notification_cooldown

    db.commit()
    db.refresh(settings)
    return settings
