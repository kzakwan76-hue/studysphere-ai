"""Runs before any test: temporary database, throwaway secret key, schema built by the real migrations."""

import os
import tempfile
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

os.environ["DATABASE_URL"] = "sqlite:///" + (Path(tempfile.mkdtemp()) / "test.db").as_posix()
os.environ["SECRET_KEY"] = "test-only-secret-key-do-not-use-anywhere-else-0123456789"

BACKEND_DIR = Path(__file__).resolve().parents[1]


def make_alembic_config(database_url: str | None = None) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", (BACKEND_DIR / "migrations").as_posix())
    if database_url:
        config.attributes["database_url"] = database_url
    return config


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    command.upgrade(make_alembic_config(), "head")


@pytest.fixture
def alembic_config_factory():
    return make_alembic_config