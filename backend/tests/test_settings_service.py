"""Regression tests for settings migration and nested updates."""
import json
import pytest
from pydantic import ValidationError
from app.dtos.settings_dtos import SettingsDTO
from app.models.user_settings import UserSettings
from app.services.settings_service import SettingsService


def test_legacy_settings_migrate_without_losing_custom_fields(db_session, test_user):
    row = UserSettings(user_id=test_user.id)
    row._settings_json = json.dumps({"theme": "light", "customLegacyValue": "keep", "shoppingList": {"autoClearChecked": "daily"}})
    db_session.add(row)
    db_session.flush()
    result = SettingsService(db_session, test_user.id).read()
    assert result.appearance.theme == "light"
    assert result.shoppingList.autoClearChecked == "manual"
    assert result.model_dump()["customLegacyValue"] == "keep"
    assert result.schemaVersion == 1


def test_nested_patch_preserves_unrelated_fields_and_other_users(db_session, test_user, second_user):
    service = SettingsService(db_session, test_user.id)
    service.write(SettingsDTO.model_validate({"recipePreferences": {"defaultSortOrder": "recent", "quickFilters": ["dinner"]}}), replace=False)
    result = service.write(SettingsDTO.model_validate({"recipePreferences": {"quickFilters": ["lunch"]}}), replace=False)
    assert result.recipePreferences.defaultSortOrder == "recent"
    assert result.recipePreferences.quickFilters == ["lunch"]
    other = SettingsService(db_session, second_user.id).read()
    assert other.recipePreferences.defaultSortOrder == "alphabetical"


def test_invalid_settings_are_rejected():
    with pytest.raises(ValidationError):
        SettingsDTO.model_validate({"appearance": {"theme": "invisible"}})


def test_install_prompt_patch_merges_and_defaults(db_session, test_user):
    service = SettingsService(db_session, test_user.id)
    assert service.read().installPrompt.installedAt is None
    service.write(SettingsDTO.model_validate({"installPrompt": {"dismissCount": 1, "snoozedUntil": "2026-10-17T00:00:00Z"}}), replace=False)
    result = service.write(SettingsDTO.model_validate({"installPrompt": {"installedAt": "2026-10-03T12:00:00Z"}}), replace=False)
    assert result.installPrompt.dismissCount == 1
    assert result.installPrompt.snoozedUntil == "2026-10-17T00:00:00Z"
    assert result.installPrompt.installedAt == "2026-10-03T12:00:00Z"
