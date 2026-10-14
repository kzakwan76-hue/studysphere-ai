import pytest
from pydantic import ValidationError

from app.config import Settings


def test_short_secret_key_is_rejected():
    with pytest.raises(ValidationError):
        Settings(secret_key="too-short")