"""Runs before any test: temporary database and uploads folder, throwaway secret key, schema from migrations."""

import os
import tempfile
from io import BytesIO
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from reportlab.pdfgen import canvas

_TEMP_DIR = Path(tempfile.mkdtemp())
os.environ["DATABASE_URL"] = "sqlite:///" + (_TEMP_DIR / "test.db").as_posix()
os.environ["UPLOADS_DIR"] = str(_TEMP_DIR / "uploads")
os.environ["SECRET_KEY"] = "test-only-secret-key-do-not-use-anywhere-else-0123456789"
os.environ["MAX_UPLOAD_MB"] = "1"  # small limits so the limit tests stay fast
os.environ["MAX_DOCUMENTS_PER_USER"] = "5"

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


@pytest.fixture
def make_pdf():
    """Build a real PDF with one page per string. An empty string gives a page with no text."""

    def build(pages: list[str]) -> bytes:
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer)
        for text in pages:
            y = 800
            for line in text.split("\n"):
                pdf.drawString(72, y, line)
                y -= 16
            pdf.showPage()
        pdf.save()
        return buffer.getvalue()

    return build