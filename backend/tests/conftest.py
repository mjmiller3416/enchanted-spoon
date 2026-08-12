"""Shared test fixtures for the Enchanted Spoon backend test suite.

Provides an in-memory SQLite database, session management, and common
test data factories.
"""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

# Import Base *and* all models so metadata.create_all creates every table
from app.database.base import Base
from app.models import (  # noqa: F401 – side-effect import registers models
    Ingredient,
    Meal,
    NutritionFacts,
    PlannerEntry,
    Recipe,
    RecipeGroup,
    RecipeHistory,
    RecipeIngredient,
    ShoppingItem,
    ShoppingItemContribution,
    UnitConversionRule,
    User,
    UserCategory,
    UserIngredientCategory,
    UserIngredientUnit,
    UserSettings,
    UserUsage,
)


# ---------------------------------------------------------------------------
# Database engine & session fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def engine():
    """Create an in-memory SQLite engine shared across the test session."""
    eng = create_engine("sqlite:///:memory:")

    # Enable FK enforcement for SQLite (matches production config)
    @event.listens_for(eng, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return eng


@pytest.fixture(scope="session")
def tables(engine):
    """Create all tables once per test session."""
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db_session(engine, tables) -> Session:
    """Provide a transactional session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, expire_on_commit=False)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# Common data factories
# ---------------------------------------------------------------------------

@pytest.fixture()
def test_user(db_session: Session) -> User:
    """Insert and return a basic test user."""
    user = User(
        clerk_id="test_clerk_001",
        email="test@example.com",
        name="Test User",
        is_admin=True,  # admin so has_pro_access is True
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def second_user(db_session: Session) -> User:
    """Insert and return a second test user for isolation tests."""
    user = User(
        clerk_id="test_clerk_002",
        email="other@example.com",
        name="Other User",
        is_admin=False,
        subscription_tier="free",
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def sample_recipe(db_session: Session, test_user: User) -> Recipe:
    """Insert and return a simple recipe (no ingredients or nutrition)."""
    recipe = Recipe(
        recipe_name="Test Pasta",
        recipe_category="Italian",
        meal_type="Dinner",
        servings=4,
        prep_time=10,
        cook_time=20,
        difficulty="Easy",
        description="A simple test pasta recipe.",
        directions="Step 1: Boil water.\nStep 2: Cook pasta.",
        user_id=test_user.id,
    )
    db_session.add(recipe)
    db_session.flush()
    return recipe


@pytest.fixture()
def sample_ingredient(db_session: Session, test_user: User) -> Ingredient:
    """Insert and return a basic ingredient."""
    ingredient = Ingredient(
        ingredient_name="Spaghetti",
        ingredient_category="Pasta",
        user_id=test_user.id,
    )
    db_session.add(ingredient)
    db_session.flush()
    return ingredient


@pytest.fixture()
def sample_meal(db_session: Session, test_user: User, sample_recipe: Recipe) -> Meal:
    """Insert and return a meal linked to the sample recipe."""
    meal = Meal(
        meal_name="Test Meal",
        main_recipe_id=sample_recipe.id,
        user_id=test_user.id,
        is_saved=True,
    )
    db_session.add(meal)
    db_session.flush()
    return meal


@pytest.fixture()
def sample_planner_entry(
    db_session: Session, test_user: User, sample_meal: Meal
) -> PlannerEntry:
    """Insert and return a planner entry linked to the sample meal."""
    entry = PlannerEntry(
        meal_id=sample_meal.id,
        user_id=test_user.id,
        position=0,
    )
    db_session.add(entry)
    db_session.flush()
    return entry


@pytest.fixture()
def sample_nutrition_data() -> dict:
    """Return a dict of realistic nutrition values for testing."""
    return {
        "calories": 350,
        "protein_g": 12.5,
        "total_fat_g": 8.0,
        "saturated_fat_g": 2.5,
        "trans_fat_g": 0.0,
        "cholesterol_mg": 25.0,
        "sodium_mg": 480.0,
        "total_carbs_g": 55.0,
        "dietary_fiber_g": 3.0,
        "total_sugars_g": 4.5,
        "is_ai_estimated": False,
    }
