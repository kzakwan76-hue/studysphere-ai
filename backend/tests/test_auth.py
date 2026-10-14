from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.main import app
from app.models import User

client = TestClient(app)
PASSWORD = "correct-horse-battery"


def register(email: str, password: str = PASSWORD):
    return client.post("/auth/register", json={"email": email, "password": password})


def login(email: str, password: str = PASSWORD):
    return client.post("/auth/login", data={"username": email, "password": password})


def test_register_returns_the_user_without_a_password():
    response = register("new@example.com")
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.com"
    assert "password" not in body and "password_hash" not in body


def test_email_is_normalised_to_lowercase():
    assert register("Mixed.Case@Example.com").json()["email"] == "mixed.case@example.com"
    assert login("MIXED.CASE@example.com").status_code == 200


def test_duplicate_email_is_rejected_case_insensitively():
    register("dupe@example.com")
    assert register("DUPE@example.com").status_code == 409


def test_short_password_is_rejected():
    assert register("short@example.com", "abc").status_code == 422


def test_invalid_email_is_rejected():
    assert register("not-an-email").status_code == 422


def test_password_is_stored_as_an_argon2_hash():
    register("hashed@example.com")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "hashed@example.com"))
        assert user is not None
        assert PASSWORD not in user.password_hash
        assert user.password_hash.startswith("$argon2")


def test_login_returns_a_token_that_opens_me():
    register("me@example.com")
    token = login("me@example.com").json()["access_token"]
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


def test_wrong_password_and_unknown_email_give_the_same_answer():
    register("exists@example.com")
    wrong_password = login("exists@example.com", "totally-wrong-password")
    unknown_email = login("nobody@example.com")
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_missing_and_garbage_tokens_are_rejected():
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer not.a.token"}).status_code == 401


def test_expired_token_is_rejected():
    user_id = register("expired@example.com").json()["id"]
    expired = jwt.encode(
        {"sub": str(user_id), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        get_settings().secret_key,
        algorithm="HS256",
    )
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_token_signed_with_another_key_is_rejected():
    user_id = register("forged@example.com").json()["id"]
    forged = jwt.encode(
        {"sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "x" * 40,
        algorithm="HS256",
    )
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401