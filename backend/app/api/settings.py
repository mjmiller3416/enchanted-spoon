"""Authenticated, validated settings endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.auth import get_current_user
from app.database.db import get_session
from app.models.user import User
from app.dtos.settings_dtos import SettingsDTO
from app.services.settings_service import SettingsService, SettingsSaveError

router = APIRouter()


def settings_service(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)) -> SettingsService:
    return SettingsService(session, current_user.id)


@router.get("", response_model=SettingsDTO)
def get_settings(service: SettingsService = Depends(settings_service)) -> SettingsDTO:
    try:
        return service.read()
    except SettingsSaveError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.put("", response_model=SettingsDTO)
def replace_settings(values: SettingsDTO, service: SettingsService = Depends(settings_service)) -> SettingsDTO:
    try:
        return service.write(values, replace=True)
    except SettingsSaveError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.patch("", response_model=SettingsDTO)
def update_settings(values: SettingsDTO, service: SettingsService = Depends(settings_service)) -> SettingsDTO:
    try:
        return service.write(values, replace=False)
    except SettingsSaveError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
