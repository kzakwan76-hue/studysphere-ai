from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.config import get_settings
from app.database import SessionLocal
from app.main import app
from app.models import LoginFailure
from app.services.throttle import record_failure, seconds_until_allowed

client = TestClient(app)
PASSWORD = "correct-horse-battery"
WRONG = "definitely-wrong-password"
SETTINGS = get_settings()


def wipe_failures() -> None:
    with SessionLocal() as db:
        db.execute(delete(LoginFailure))
        db.commit()


@pytest.fixture(autouse=True)
def clean_failures():
    # All HTTP tests share one client IP, so every test starts and ends with a clean slate.
    wipe_failures()
    yield
    wipe_failures()


def register(email: str) -> None:
    client.post("/auth/register", json={"email": email, "password": PASSWORD})


def attempt(email: str, password: str):
    return client.post("/auth/login", data={"username": email, "password": password})


def test_repeated_failures_lock_out_even_the_right_password():
    register("lock@example.com")
    for _ in range(SETTINGS.login_max_failures):
        assert attempt("lock@example.com", WRONG).status_code == 401
    locked = attempt("lock@example.com", PASSWORD)
    assert locked.status_code == 429
    assert int(locked.headers["Retry-After"]) > 0


def test_unknown_emails_are_throttled_too_so_nothing_is_revealed():
    for _ in range(SETTINGS.login_max_failures):
        assert attempt("ghost@example.com", WRONG).status_code == 401
    assert attempt("ghost@example.com", WRONG).status_code == 429


def test_successful_login_clears_the_failure_count():
    register("clear@example.com")
    for _ in range(SETTINGS.login_max_failures - 2):
        assert attempt("clear@example.com", WRONG).status_code == 401
    assert attempt("clear@example.com", PASSWORD).status_code == 200
    for _ in range(SETTINGS.login_max_failures - 1):  # would have locked without the reset
        assert attempt("clear@example.com", WRONG).status_code == 401


def test_locking_one_account_does_not_block_another():
    register("victim@example.com")
    register("neighbour@example.com")
    for _ in range(SETTINGS.login_max_failures):
        attempt("victim@example.com", WRONG)
    assert attempt("victim@example.com", PASSWORD).status_code == 429
    assert attempt("neighbour@example.com", PASSWORD).status_code == 200


def test_per_ip_limit_stops_guessing_across_many_accounts():
    for number in range(SETTINGS.login_max_failures_per_ip):
        assert attempt(f"stuffing{number}@example.com", WRONG).status_code == 401
    assert attempt("fresh@example.com", WRONG).status_code == 429


def test_old_failures_do_not_count():
    register("expired@example.com")
    old = datetime.now(timezone.utc) - timedelta(minutes=SETTINGS.login_window_minutes + 5)
    with SessionLocal() as db:
        db.add_all(
            LoginFailure(email="expired@example.com", ip="testclient", created_at=old)
            for _ in range(SETTINGS.login_max_failures)
        )
        db.commit()
    assert attempt("expired@example.com", PASSWORD).status_code == 200


def test_lock_lifts_exactly_when_the_window_passes():
    start = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    window = timedelta(minutes=SETTINGS.login_window_minutes)
    with SessionLocal() as db:
        for _ in range(SETTINGS.login_max_failures):
            record_failure(db, "timer@example.com", "10.1.1.1", now=start)
        assert seconds_until_allowed(db, "timer@example.com", "10.1.1.1", now=start) == int(window.total_seconds())
        assert seconds_until_allowed(db, "timer@example.com", "10.1.1.1", now=start + window - timedelta(seconds=1)) == 1
        assert seconds_until_allowed(db, "timer@example.com", "10.1.1.1", now=start + window) == 0