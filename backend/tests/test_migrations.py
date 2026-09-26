"""A brand-new environment must be able to build its schema from migrations.

The Docker start script runs `alembic upgrade head` under `set -e`, so a
migration that only works against an already-populated database would
crash-loop any fresh deployment (new staging DB, restore to an empty DB).
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_upgrade_head_on_empty_database(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'fresh.db'}"
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URL", url)
    monkeypatch.chdir(BACKEND_DIR)

    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")

    tables = set(inspect(create_engine(url)).get_table_names())
    assert {"users", "recipe", "meals", "planner_entries", "shopping_items"} <= tables
    assert "shopping_states" not in tables
