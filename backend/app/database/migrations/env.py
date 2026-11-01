""" app/database/migrations/env.py
Alembic migration environment setup for the recipe_app project.

This script configures the Alembic migration context, loads environment variables,
and ensures that all SQLAlchemy models are registered for migrations. It supports
both offline and online migration modes.

Key functionalities:
- Loads environment variables from a .env file located at the project root.
- Adds the project root to sys.path for module resolution.
- Configures the Alembic context with the database URL, using DATABASE_URL from
    the environment if available.
- Imports SQLAlchemy models to register their metadata for migrations.
- Defines functions to run migrations in both offline and online modes.

Usage:
This script is automatically invoked by Alembic when running migration commands.
"""

import os
import sys
# ── Imports ─────────────────────────────────────────────────────────────────────────────
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# Path: app/database/migrations/env.py
# parents[0]=migrations, parents[1]=database, parents[2]=app, parents[3]=backend
backend_root = Path(__file__).resolve().parents[3]

# load .env file from backend root
load_dotenv(dotenv_path=backend_root / ".env")

# add backend root to sys.path so 'app' module can be found
sys.path.insert(0, str(backend_root))

# ── Alembic Config ──────────────────────────────────────────────────────────────────────
config = context.config
fileConfig(config.config_file_name)

# Override URL if SQLALCHEMY_DATABASE_URL is set (matches db.py)
database_url = os.getenv("SQLALCHEMY_DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# ── Import metadata ─────────────────────────────────────────────────────────────────────
from app.database.base import Base
from app.models.household import Household, HouseholdInvite, HouseholdMember, HouseholdRecipeShare
from app.models.ingredient import Ingredient
# import all models to register them with metadata
from app.models.meal import Meal
from app.models.planner_entry import PlannerEntry
from app.models.recipe import Recipe
from app.models.recipe_history import RecipeHistory
from app.models.recipe_ingredient import RecipeIngredient
from app.models.shopping_item import ShoppingItem
from app.models.shopping_item_contribution import ShoppingItemContribution
from app.models.user import User
from app.models.user_settings import UserSettings

target_metadata = Base.metadata

# ── Run Migrations ──────────────────────────────────────────────────────────────────────
def run_migrations_offline():
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
