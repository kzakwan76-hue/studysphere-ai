import pytest
from fastapi.testclient import TestClient

from app.api.ask import get_ask_limiter, get_llm_provider
from app.main import app
from app.services.ratelimit import SlidingWindowLimiter

client = TestClient(app)
PASSWORD = "correct-horse-battery"
NOTES = b"Binary search halves the list at every step. It needs a sorted list."


@pytest.fixture(autouse=True)
def reset_overrides():
    yield
    app.dependency_overrides.clear()


def auth_headers(email: str) -> dict[str, str]:
    client.post("/auth/register", json={"email": email, "password": PASSWORD})
    response = client.post("/auth/login", data={"username": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def upload(headers: dict[str, str], name: str, data: bytes):
    return client.post("/documents", files={"file": (name, data, "text/plain")}, headers=headers)


def ask(headers: dict[str, str], question: str = "How does binary search work?", **extra):
    return client.post("/ask", json={"question": question, **extra}, headers=headers)


def use_provider(provider) -> None:
    app.dependency_overrides[get_llm_provider] = lambda: provider


def test_an_unrelated_question_is_refused_without_calling_the_model(fake_provider):
    provider = fake_provider(reply="Should never be used [1].")
    use_provider(provider)
    headers = auth_headers("ask-refuse@example.com")
    upload(headers, "notes.txt", NOTES)
    body = ask(headers, "What is the capital of Australia?").json()
    assert body["status"] == "not_found" and body["sources"] == [] and body["answer"] is None
    assert provider.calls == []


def test_without_a_provider_the_best_passages_are_returned():
    headers = auth_headers("ask-nomodel@example.com")
    upload(headers, "notes.txt", NOTES)
    body = ask(headers).json()
    assert body["status"] == "passages_only" and body["answer"] is None and body["provider"] is None
    assert body["sources"][0]["filename"] == "notes.txt" and body["sources"][0]["cited"] is False


def test_a_grounded_answer_is_returned_with_its_sources(fake_provider):
    provider = fake_provider(reply="Binary search halves the list at every step [1].")
    use_provider(provider)
    headers = auth_headers("ask-answer@example.com")
    upload(headers, "notes.txt", NOTES)
    body = ask(headers).json()
    assert body["status"] == "answered" and "halves" in body["answer"]
    assert body["sources"][0]["cited"] is True and body["provider"] == "fake"
    assert body["warnings"] == [] and len(provider.calls) == 1


def test_another_users_documents_are_never_used(fake_provider):
    provider = fake_provider(reply="Should never be used [1].")
    use_provider(provider)
    owner = auth_headers("ask-owner@example.com")
    other = auth_headers("ask-other@example.com")
    upload(owner, "notes.txt", NOTES)
    body = ask(other).json()
    assert body["status"] == "not_found" and body["sources"] == []
    assert provider.calls == []


def test_document_filter_checks_ownership():
    owner = auth_headers("ask-doc-owner@example.com")
    other = auth_headers("ask-doc-other@example.com")
    document_id = upload(owner, "notes.txt", NOTES).json()["id"]
    assert ask(owner, document_id=document_id).status_code == 200
    assert ask(other, document_id=document_id).status_code == 404
    assert ask(owner, document_id=999999).status_code == 404


def test_invalid_requests_are_rejected():
    headers = auth_headers("ask-validation@example.com")
    assert client.post("/ask", json={"question": "hi"}, headers=headers).status_code == 422
    assert client.post("/ask", json={}, headers=headers).status_code == 422
    assert client.post("/ask", json={"question": "x" * 501}, headers=headers).status_code == 422


def test_asking_requires_login():
    assert client.post("/ask", json={"question": "anything at all"}).status_code == 401


def test_asking_is_rate_limited_per_user():
    limiter = SlidingWindowLimiter(max_events=2, window_seconds=3600)
    app.dependency_overrides[get_ask_limiter] = lambda: limiter
    headers = auth_headers("ask-limited@example.com")
    assert ask(headers).status_code == 200
    assert ask(headers).status_code == 200
    limited = ask(headers)
    assert limited.status_code == 429 and int(limited.headers["Retry-After"]) > 0