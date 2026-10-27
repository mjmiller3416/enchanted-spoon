"""Tests for Genie's add_meals_to_planner tool (MealPlanningMixin).

Covers:
- Planning flow: write happens with validated picks, reply reflects what landed
- Guard rails: full planner, empty library, failed planning call, failed write,
  no usable picks, legacy callers without writers
- Pick validation: unknown ids, repeated mains, side clean-up, meal limit
- Planning call: prompt contents, structured-output config, JSON parsing
- Recipe catalog: favorites first, key ingredients, per-user isolation
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from google.genai import types

from app.dtos.planner_dtos import PlannerEntryResponseDTO
from app.models.ingredient import Ingredient
from app.models.recipe import Recipe
from app.models.recipe_ingredient import RecipeIngredient
from app.repositories.planner import MAX_PLANNER_ENTRIES
from app.services.ai.assistant import AssistantService
from app.services.ai.assistant.planning import MEAL_PLAN_SCHEMA, PLANNER_FAILED_REPLY
from app.services.ai.user_context_builder import UserContextBuilder

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CATALOG = [
    {"id": 1, "name": "Beef Tacos", "category": "beef", "meal_type": "dinner",
     "total_time": 30, "is_favorite": True, "ingredients": ["Ground Beef", "Tortillas"]},
    {"id": 2, "name": "Spaghetti Bolognese", "category": "beef", "meal_type": "dinner",
     "total_time": 45, "is_favorite": False, "ingredients": ["Ground Beef", "Spaghetti"]},
    {"id": 3, "name": "Chicken Parm", "category": "chicken", "meal_type": "dinner",
     "total_time": None, "is_favorite": False, "ingredients": []},
    {"id": 10, "name": "Mexican Rice", "category": "vegetarian", "meal_type": "side",
     "total_time": 25, "is_favorite": False, "ingredients": ["Rice"]},
    {"id": 11, "name": "Garlic Bread", "category": "vegetarian", "meal_type": "side",
     "total_time": 15, "is_favorite": False, "ingredients": ["Bread"]},
    {"id": 12, "name": "Caesar Salad", "category": "vegetarian", "meal_type": "side",
     "total_time": 10, "is_favorite": False, "ingredients": ["Romaine"]},
    {"id": 13, "name": "Street Corn", "category": "vegetarian", "meal_type": "side",
     "total_time": 20, "is_favorite": False, "ingredients": ["Corn"]},
]
CATALOG_BY_ID = {r["id"]: r for r in CATALOG}


def _make_service() -> AssistantService:
    """Build a service instance without running __init__ (skips client setup)."""
    return AssistantService.__new__(AssistantService)


def _entries(meals):
    """Planner entry DTOs as add_new_meals_to_planner would return them."""
    return [
        PlannerEntryResponseDTO(
            id=100 + i, meal_id=200 + i, position=i, is_completed=False,
            completed_at=None, scheduled_date=None, meal_name=m.meal_name,
            main_recipe_id=m.main_recipe_id, side_recipe_ids=m.side_recipe_ids,
        )
        for i, m in enumerate(meals)
    ]


async def _plan(service, args, *, plan=None, context=None, catalog=CATALOG, adder=None):
    """Run the tool with a stubbed planning call and model follow-up."""
    if plan is not None:
        service._request_meal_plan = MagicMock(return_value=plan)
    # Keep a test's own follow-up stub if it set one
    if not isinstance(service._finalize_after_tool_call, MagicMock):
        service._finalize_after_tool_call = MagicMock(return_value="Planned! 📅")
    adder = adder or MagicMock(side_effect=_entries)
    out = await service._handle_function_call(
        "add_meals_to_planner",
        args,
        context if context is not None else {"meal_plan": []},
        [],
        None,
        load_recipe_catalog=MagicMock(return_value=catalog),
        add_planner_meals=adder,
    )
    return out, adder


# ---------------------------------------------------------------------------
# Planning flow
# ---------------------------------------------------------------------------

async def test_planned_meals_are_written_and_reported():
    """Validated picks are written, and the model confirms the real outcome."""
    service = _make_service()
    plan = {
        "meals": [
            {"main_recipe_id": 1, "side_recipe_ids": [10, 13]},
            {"main_recipe_id": 2, "side_recipe_ids": [11]},
        ],
        "notes": "No chicken pasta saved.",
    }

    out, adder = await _plan(
        service, {"meal_count": 2, "requirements": "beef, 1-2 sides"}, plan=plan
    )

    meals = adder.call_args.args[0]
    assert [(m.meal_name, m.main_recipe_id, m.side_recipe_ids) for m in meals] == [
        ("Beef Tacos", 1, [10, 13]),
        ("Spaghetti Bolognese", 2, [11]),
    ]
    assert service._finalize_after_tool_call.call_args.kwargs["result"] == {
        "added_meals": [
            {"main": "Beef Tacos", "sides": ["Mexican Rice", "Street Corn"]},
            {"main": "Spaghetti Bolognese", "sides": ["Garlic Bread"]},
        ],
        "notes": "No chicken pasta saved.",
        "not_added_planner_full": 0,
    }
    assert out["type"] == "planner"
    assert out["response"] == "Planned! 📅"
    assert [e.id for e in out["planner_update"]] == [100, 101]


async def test_request_is_passed_to_the_planning_call():
    service = _make_service()
    planned = [{"meal_name": "Pot Roast", "main_recipe_name": "Pot Roast"}]

    await _plan(
        service,
        {"meal_count": "4", "requirements": "3 ground beef, 1 chicken"},
        plan={"meals": [], "notes": ""},
        context={"meal_plan": planned},
    )

    service._request_meal_plan.assert_called_once_with(
        "3 ground beef, 1 chicken", 4, CATALOG, planned
    )


async def test_meal_count_is_capped_to_open_planner_slots():
    """Only what fits is planned; the reply is told how many didn't fit."""
    service = _make_service()
    planned = [{"meal_name": f"M{i}", "main_recipe_name": f"M{i}"}
               for i in range(MAX_PLANNER_ENTRIES - 1)]

    out, adder = await _plan(
        service,
        {"meal_count": 3, "requirements": "anything"},
        plan={"meals": [{"main_recipe_id": 1, "side_recipe_ids": []},
                        {"main_recipe_id": 2, "side_recipe_ids": []}], "notes": ""},
        context={"meal_plan": planned},
    )

    assert service._request_meal_plan.call_args.args[1] == 1
    assert len(adder.call_args.args[0]) == 1
    assert service._finalize_after_tool_call.call_args.kwargs["result"][
        "not_added_planner_full"
    ] == 2
    assert out["type"] == "planner"


# ---------------------------------------------------------------------------
# Guard rails
# ---------------------------------------------------------------------------

async def test_full_planner_skips_planning():
    service = _make_service()
    service._request_meal_plan = MagicMock()
    planned = [{"meal_name": "M", "main_recipe_name": "M"}] * MAX_PLANNER_ENTRIES

    out, adder = await _plan(
        service, {"meal_count": 2, "requirements": "x"}, context={"meal_plan": planned}
    )

    service._request_meal_plan.assert_not_called()
    adder.assert_not_called()
    assert out["type"] == "chat"
    assert "full" in out["response"]


async def test_empty_library_skips_planning():
    service = _make_service()
    service._request_meal_plan = MagicMock()

    out, adder = await _plan(service, {"meal_count": 2, "requirements": "x"}, catalog=[])

    service._request_meal_plan.assert_not_called()
    adder.assert_not_called()
    assert out["type"] == "chat"
    assert "saved recipes" in out["response"]


async def test_failed_planning_call_writes_nothing():
    service = _make_service()
    service._finalize_after_tool_call = MagicMock()
    service._request_meal_plan = MagicMock(return_value=None)

    out, adder = await _plan(service, {"meal_count": 2, "requirements": "x"})

    adder.assert_not_called()
    service._finalize_after_tool_call.assert_not_called()
    assert out["type"] == "chat"
    assert "planner_update" not in out


async def test_no_usable_picks_explains_without_writing():
    """Nothing valid came back: Genie explains the gap and nothing is written."""
    service = _make_service()

    out, adder = await _plan(
        service,
        {"meal_count": 1, "requirements": "lamb"},
        plan={"meals": [{"main_recipe_id": 999, "side_recipe_ids": []}],
              "notes": "No lamb recipes saved."},
    )

    adder.assert_not_called()
    assert service._finalize_after_tool_call.call_args.kwargs["result"] == {
        "added_meals": [], "notes": "No lamb recipes saved."
    }
    assert out["type"] == "chat"
    assert "planner_update" not in out


async def test_failed_write_never_claims_success():
    """A raising writer gets a canned apology without asking the model."""
    service = _make_service()
    service._finalize_after_tool_call = MagicMock()

    out, _ = await _plan(
        service,
        {"meal_count": 1, "requirements": "x"},
        plan={"meals": [{"main_recipe_id": 1, "side_recipe_ids": []}], "notes": ""},
        adder=MagicMock(side_effect=RuntimeError("db down")),
    )

    service._finalize_after_tool_call.assert_not_called()
    assert out == {"type": "chat", "response": PLANNER_FAILED_REPLY,
                   "tool_args": {"meal_count": 1, "requirements": "x"}}


async def test_without_writers_does_not_crash():
    """Callers that don't supply the planner hooks (legacy endpoint) get a graceful reply."""
    service = _make_service()

    out = await service._handle_function_call(
        "add_meals_to_planner", {"meal_count": 1, "requirements": "x"}, None, [], None
    )

    assert out["type"] == "chat"
    assert "planner_update" not in out


# ---------------------------------------------------------------------------
# Pick validation
# ---------------------------------------------------------------------------

def test_parse_drops_unknown_ids_and_repeated_mains():
    meals = AssistantService._parse_meal_plan(
        [
            {"main_recipe_id": 999, "side_recipe_ids": [10]},  # not in library
            {"main_recipe_id": 1, "side_recipe_ids": [10]},
            {"main_recipe_id": 1, "side_recipe_ids": [11]},    # repeat main
            "garbage",
            {"main_recipe_id": "2", "side_recipe_ids": None},  # string id, no sides
        ],
        CATALOG_BY_ID,
        limit=5,
    )

    assert [(m.main_recipe_id, m.side_recipe_ids) for m in meals] == [(1, [10]), (2, [])]


def test_parse_cleans_up_sides():
    """Unknown, repeated and main-as-side ids are dropped; at most 3 remain."""
    (meal,) = AssistantService._parse_meal_plan(
        [{"main_recipe_id": 1, "side_recipe_ids": [1, 10, 10, 999, 11, 12, 13]}],
        CATALOG_BY_ID,
        limit=1,
    )

    assert meal.side_recipe_ids == [10, 11, 12]
    assert meal.is_saved is False


def test_parse_stops_at_limit_and_tolerates_bad_shapes():
    plan = [{"main_recipe_id": i, "side_recipe_ids": []} for i in (1, 2, 3)]

    assert len(AssistantService._parse_meal_plan(plan, CATALOG_BY_ID, limit=2)) == 2
    assert AssistantService._parse_meal_plan(None, CATALOG_BY_ID, limit=2) == []
    assert AssistantService._parse_meal_plan({"meals": plan}, CATALOG_BY_ID, limit=2) == []


def test_fallback_text_lists_meals_and_gaps():
    text = AssistantService._describe_planner_update({
        "added_meals": [
            {"main": "Beef Tacos", "sides": ["Mexican Rice", "Street Corn"]},
            {"main": "Chicken Parm", "sides": []},
        ],
        "notes": "No Mexican chicken saved.",
        "not_added_planner_full": 0,
    })

    assert text == (
        "Added 2 meals to your planner! 📅\n\n"
        "- **Beef Tacos** — Mexican Rice, Street Corn\n"
        "- **Chicken Parm**\n\n"
        "No Mexican chicken saved."
    )


# ---------------------------------------------------------------------------
# Planning call
# ---------------------------------------------------------------------------

def _gemini_returning(text):
    """A mock Gemini client whose generate_content returns one text part."""
    part = MagicMock(thought=False, text=text)
    response = MagicMock()
    response.candidates = [MagicMock(content=MagicMock(parts=[part]))]
    client = MagicMock()
    client.models.generate_content.return_value = response
    return client


def test_planning_call_sends_library_and_parses_json():
    service = _make_service()
    plan = {"meals": [{"main_recipe_id": 1, "side_recipe_ids": [10]}], "notes": ""}
    client = _gemini_returning(json.dumps(plan))

    with patch("app.services.ai.assistant.planning.get_gemini_client", return_value=client):
        result = service._request_meal_plan(
            "3 ground beef", 4, CATALOG,
            [{"meal_name": "Pot Roast", "main_recipe_name": "Pot Roast"}],
        )

    assert result == plan
    kwargs = client.models.generate_content.call_args.kwargs
    prompt = kwargs["contents"][0]["parts"][0]["text"]
    assert "3 ground beef" in prompt
    assert "Plan exactly 4 meal(s)" in prompt
    assert "- Pot Roast (Pot Roast)" in prompt
    assert "1 | Beef Tacos | beef | dinner | 30min | ★ | Ground Beef, Tortillas" in prompt
    assert "3 | Chicken Parm | chicken | dinner | - |  | " in prompt
    assert kwargs["config"]["response_mime_type"] == "application/json"
    assert kwargs["config"]["response_schema"] is MEAL_PLAN_SCHEMA


@pytest.mark.parametrize("text", ["not json", "[1, 2]", None])
def test_planning_call_rejects_unusable_output(text):
    service = _make_service()

    with patch(
        "app.services.ai.assistant.planning.get_gemini_client",
        return_value=_gemini_returning(text),
    ):
        assert service._request_meal_plan("x", 1, CATALOG, []) is None


def test_planning_schema_is_accepted_by_the_sdk():
    """The SDK validates the dict into a Schema at request time; a bad shape would fail there."""
    schema = types.Schema.model_validate(MEAL_PLAN_SCHEMA)

    meal = schema.properties["meals"].items
    assert meal.properties["side_recipe_ids"].items.type == types.Type.INTEGER
    assert meal.required == ["main_recipe_id", "side_recipe_ids"]


# ---------------------------------------------------------------------------
# Recipe catalog
# ---------------------------------------------------------------------------

def test_recipe_catalog_lists_favorites_first_with_ingredients(
    db_session, test_user, second_user
):
    beef = Ingredient(ingredient_name="Ground Beef", ingredient_category="meat",
                      user_id=test_user.id)
    db_session.add(beef)
    older = Recipe(recipe_name="Meatloaf", recipe_category="beef", meal_type="dinner",
                   user_id=test_user.id, prep_time=10, cook_time=50)
    newer = Recipe(recipe_name="Coleslaw", recipe_category="vegetarian", meal_type="side",
                   user_id=test_user.id)
    favorite = Recipe(recipe_name="Tacos", recipe_category="beef", meal_type="dinner",
                      user_id=test_user.id, is_favorite=True)
    foreign = Recipe(recipe_name="Not Mine", recipe_category="beef", meal_type="dinner",
                     user_id=second_user.id)
    for recipe in (favorite, older, newer, foreign):
        db_session.add(recipe)
        db_session.flush()
    db_session.add(RecipeIngredient(recipe_id=older.id, ingredient_id=beef.id))
    db_session.flush()
    db_session.expire_all()

    catalog = UserContextBuilder(db_session, test_user.id).build_recipe_catalog()

    assert [r["name"] for r in catalog] == ["Tacos", "Coleslaw", "Meatloaf"]
    assert catalog[2] == {
        "id": older.id, "name": "Meatloaf", "category": "beef", "meal_type": "dinner",
        "total_time": 60, "is_favorite": False, "ingredients": ["Ground Beef"],
    }
