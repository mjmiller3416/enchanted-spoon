"""Tests for the account-synced "What's new" read state.

The frontend seeds `whatsNew.lastSeenRelease` from the account's creation
date, so both the settings section and `created_at` on /api/users/me matter.
"""
from app.dtos.admin_dtos import CurrentUserDTO
from app.dtos.settings_dtos import SettingsDTO
from app.services.settings_service import SettingsService


def test_whats_new_defaults_to_unseen(db_session, test_user):
    settings = SettingsService(db_session, test_user.id).read()
    assert settings.whatsNew.lastSeenRelease is None


def test_whats_new_patch_persists_without_touching_other_sections(db_session, test_user, second_user):
    service = SettingsService(db_session, test_user.id)
    service.write(SettingsDTO.model_validate({"installPrompt": {"dismissCount": 1}}), replace=False)
    result = service.write(SettingsDTO.model_validate({"whatsNew": {"lastSeenRelease": "2026-09-30"}}), replace=False)
    assert result.whatsNew.lastSeenRelease == "2026-09-30"
    assert result.installPrompt.dismissCount == 1
    assert SettingsService(db_session, test_user.id).read().whatsNew.lastSeenRelease == "2026-09-30"
    assert SettingsService(db_session, second_user.id).read().whatsNew.lastSeenRelease is None


def test_dismissed_spotlights_default_empty_and_replace_on_patch(db_session, test_user):
    service = SettingsService(db_session, test_user.id)
    assert service.read().whatsNew.dismissedSpotlights == []
    service.write(SettingsDTO.model_validate({"whatsNew": {"lastSeenRelease": "2026-09-30"}}), replace=False)
    result = service.write(SettingsDTO.model_validate({"whatsNew": {"dismissedSpotlights": ["shopping-notes"]}}), replace=False)
    assert result.whatsNew.dismissedSpotlights == ["shopping-notes"]
    assert result.whatsNew.lastSeenRelease == "2026-09-30"


def test_current_user_dto_exposes_account_creation_date(test_user):
    dto = CurrentUserDTO.from_model(test_user)
    assert dto.created_at == test_user.created_at
    assert "created_at" in dto.model_dump(mode="json")
