from fastapi import APIRouter, Depends, status, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.interaction import (
    InteractionCreate,
    InteractionResponse,
    InteractionListResponse,
)
from app.services.auth_service import get_current_user
from app.services.interaction_service import InteractionService

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.post("", response_model=InteractionResponse)
def create_interaction(
    data: InteractionCreate,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    interaction, is_created = InteractionService.record_interaction(
        db=db,
        user_id=current_user.id,
        data=data
    )
    if is_created:
        response.status_code = status.HTTP_201_CREATED
    else:
        # Idempotent response for duplicate event
        response.status_code = status.HTTP_200_OK

    return interaction


@router.get("", response_model=InteractionListResponse)
def list_interactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    items, total = InteractionService.get_user_interactions(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size
    )
    return InteractionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.delete("/{interaction_id}")
def delete_interaction(
    interaction_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    InteractionService.delete_interaction(
        db=db,
        user_id=current_user.id,
        interaction_id=interaction_id
    )
    return {"message": "Interaction removed and preference profile updated"}
