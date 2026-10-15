import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
PASSWORD = "correct-horse-battery"


def auth_headers(email: str) -> dict[str, str]:
    client.post("/auth/register", json={"email": email, "password": PASSWORD})
    response = client.post("/auth/login", data={"username": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def upload(headers: dict[str, str], name: str, data: bytes, content_type: str = "text/plain"):
    return client.post("/documents", files={"file": (name, data, content_type)}, headers=headers)


def test_search_finds_the_right_document_and_page(make_pdf):
    headers = auth_headers("search-owner@example.com")
    pdf = make_pdf(["Binary search halves the search space.", "Hash tables give constant time lookups."])
    upload(headers, "algorithms.pdf", pdf, "application/pdf")

    body = client.get("/search", params={"q": "how do hash tables work"}, headers=headers).json()

    assert body["terms"] == ["hash", "table", "work"]
    top = body["results"][0]
    assert top["filename"] == "algorithms.pdf" and top["page_number"] == 2
    assert "Hash" in top["text"]
    assert top["matched_terms"] == ["hash", "table"]
    assert top["coverage"] == pytest.approx(2 / 3)


def test_search_never_returns_another_users_documents():
    owner = auth_headers("search-private-owner@example.com")
    other = auth_headers("search-private-other@example.com")
    upload(owner, "bio.txt", b"Photosynthesis happens in chloroplasts.")
    assert client.get("/search", params={"q": "photosynthesis"}, headers=owner).json()["results"] != []
    assert client.get("/search", params={"q": "photosynthesis"}, headers=other).json()["results"] == []


def test_document_filter_restricts_results_and_checks_ownership():
    owner = auth_headers("search-filter-owner@example.com")
    other = auth_headers("search-filter-other@example.com")
    first = upload(owner, "first.txt", b"alpha beta gamma delta").json()["id"]
    upload(owner, "second.txt", b"alpha epsilon zeta eta")

    everywhere = client.get("/search", params={"q": "alpha"}, headers=owner).json()["results"]
    assert {hit["filename"] for hit in everywhere} == {"first.txt", "second.txt"}
    only_first = client.get("/search", params={"q": "alpha", "document_id": first}, headers=owner).json()["results"]
    assert {hit["filename"] for hit in only_first} == {"first.txt"}

    assert client.get("/search", params={"q": "alpha", "document_id": first}, headers=other).status_code == 404
    assert client.get("/search", params={"q": "alpha", "document_id": 999999}, headers=owner).status_code == 404


def test_search_requires_login():
    assert client.get("/search", params={"q": "anything"}).status_code == 401


def test_invalid_parameters_are_rejected():
    headers = auth_headers("search-validation@example.com")
    assert client.get("/search", headers=headers).status_code == 422
    assert client.get("/search", params={"q": "a"}, headers=headers).status_code == 422
    assert client.get("/search", params={"q": "x" * 301}, headers=headers).status_code == 422
    assert client.get("/search", params={"q": "valid", "limit": 0}, headers=headers).status_code == 422
    assert client.get("/search", params={"q": "valid", "limit": 21}, headers=headers).status_code == 422


def test_a_question_made_only_of_filler_words_returns_nothing():
    headers = auth_headers("search-filler@example.com")
    upload(headers, "any.txt", b"Some notes about anything at all.")
    body = client.get("/search", params={"q": "what is the"}, headers=headers).json()
    assert body["terms"] == [] and body["results"] == []


def test_results_expose_only_the_expected_fields():
    headers = auth_headers("search-fields@example.com")
    upload(headers, "fields.txt", b"Checking which fields appear in a search result.")
    hit = client.get("/search", params={"q": "search result fields"}, headers=headers).json()["results"][0]
    assert set(hit) == {
        "chunk_id", "document_id", "filename", "page_number", "score", "coverage", "matched_terms", "text",
    }