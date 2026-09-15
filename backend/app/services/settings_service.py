"""Settings normalization and nested updates; services own transactions."""
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.dtos.settings_dtos import SettingsDTO
from app.repositories.user_repo import UserRepo


class SettingsSaveError(Exception):
    """Settings could not be persisted."""


def merge_settings(current: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Merge nested fields without replacing unrelated preferences."""
    result = dict(current)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_settings(result[key], value)
        else:
            result[key] = value
    return result


class SettingsService:
    def __init__(self, session: Session, user_id: int) -> None:
        self.session = session
        self.user_id = user_id
        self.repo = UserRepo(session)

    def read(self) -> SettingsDTO:
        return self._save(None, replace=False)

    def write(self, values: SettingsDTO, *, replace: bool) -> SettingsDTO:
        return self._save(values, replace=replace)

    def _save(self, values: SettingsDTO | None, *, replace: bool) -> SettingsDTO:
        try:
            row = self.repo.get_or_create_settings(self.user_id, for_update=True)
            current = SettingsDTO.model_validate(row.settings).model_dump()
            if values is not None:
                patch = values.model_dump(exclude_unset=True)
                current = patch if replace else merge_settings(current, patch)
            normalized = SettingsDTO.model_validate(current)
            row.settings = normalized.model_dump()
            self.session.commit()
            return normalized
        except SQLAlchemyError as error:
            self.session.rollback()
            raise SettingsSaveError("Settings could not be saved. Please retry.") from error
