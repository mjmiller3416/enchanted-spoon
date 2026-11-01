"""Register native push tokens for the signed-in account."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.db import get_session
from app.models.user import User
from app.services.push_service import PushService

router = APIRouter()


class DeviceTokenRequestDTO(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    platform: str = Field(pattern="^(ios|android)$")


class DeviceTokenResponseDTO(BaseModel):
    id: int
    platform: str


@router.post("", response_model=DeviceTokenResponseDTO)
def register_device_token(
    body: DeviceTokenRequestDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Save the APNs or FCM token for this account."""
    service = PushService(session)
    try:
        row = service.register_token(current_user, body.token, body.platform)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session.commit()
    return DeviceTokenResponseDTO(id=row.id, platform=row.platform)


@router.delete("")
def unregister_device_token(
    body: DeviceTokenRequestDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Drop a token when the user signs out or disables notifications."""
    PushService(session).unregister_token(current_user, body.token)
    session.commit()
    return {"removed": True}
