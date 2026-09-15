import pytest
from pydantic import ValidationError
from app.dtos.planner_dtos import PlannerShoppingModeDTO
from app.dtos.shopping_dtos import ManualItemCreateDTO, ShoppingItemUpdateDTO
from app.services.planner import PlannerService
from app.services.planner.entry import EntryNotFoundError
from app.services.shopping import ShoppingService


@pytest.mark.parametrize("mode", ["all", "produce_only", "none"])
def test_shopping_mode_is_repeatable(db_session, test_user, sample_planner_entry, mode):
    service = PlannerService(db_session, test_user.id)
    data = PlannerShoppingModeDTO(shopping_mode=mode)
    assert service.set_shopping_mode(sample_planner_entry.id, data).shopping_mode == mode
    assert service.set_shopping_mode(sample_planner_entry.id, data).shopping_mode == mode


def test_shopping_mode_enforces_owner_and_validation(db_session, second_user, sample_planner_entry):
    with pytest.raises(EntryNotFoundError):
        PlannerService(db_session, second_user.id).set_shopping_mode(sample_planner_entry.id, PlannerShoppingModeDTO(shopping_mode="none"))
    with pytest.raises(ValidationError):
        PlannerShoppingModeDTO(shopping_mode="unexpected")


def test_item_flag_and_collected_updates_are_repeatable(db_session, test_user):
    service = ShoppingService(db_session, test_user.id)
    item = service.add_manual_item(ManualItemCreateDTO(ingredient_name="Test apples", quantity=2, category="produce"))
    for _ in range(2):
        result = service.update_item(item.id, ShoppingItemUpdateDTO(flagged=True, have=True))
        assert result.flagged and result.have
    result = service.update_item(item.id, ShoppingItemUpdateDTO(flagged=False))
    assert not result.flagged and result.have
