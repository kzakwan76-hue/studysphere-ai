from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.config import get_settings
from app.database import SessionLocal
from app.main import app
from app.models import Chunk, Document

client = TestClient(app)
PASSWORD = "correct-horse-battery"


def auth_headers(email: str) -> dict[str, str]:
    client.post("/auth/register", json={"email": email, "password": PASSWORD})
    response = client.post("/auth/login", data={"username": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def upload(headers: dict[str, str], name: str, data: bytes, content_type: str = "application/octet-stream"):
    return client.post("/documents", files={"file": (name, data, content_type)}, headers=headers)


def test_text_upload_creates_a_document_with_chunks():
    headers = auth_headers("docs-text@example.com")
    response = upload(headers, "notes.txt", b"Binary search halves the search space each step.")
    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "notes.txt"
    assert body["kind"] == "text" and body["page_count"] == 1 and body["chunk_count"] == 1
    assert "storage_path" not in body and "sha256" not in body


def test_pdf_upload_keeps_page_numbers(make_pdf):
    headers = auth_headers("docs-pdf@example.com")
    data = make_pdf(["Binary search halves the search space.", "Hash tables give constant time lookups."])
    body = upload(headers, "algorithms.pdf", data, "application/pdf").json()
    assert body["page_count"] == 2
    chunks = client.get(f"/documents/{body['id']}/chunks", headers=headers).json()
    assert [chunk["page_number"] for chunk in chunks] == [1, 2]
    assert "Binary" in chunks[0]["text"] and "Hash" in chunks[1]["text"]


def test_documents_are_private_to_their_owner():
    owner = auth_headers("docs-owner@example.com")
    other = auth_headers("docs-other@example.com")
    document_id = upload(owner, "private.txt", b"Only the owner may read this.").json()["id"]
    assert client.get("/documents", headers=other).json() == []
    for method, path in [
        ("GET", f"/documents/{document_id}"),
        ("GET", f"/documents/{document_id}/chunks"),
        ("DELETE", f"/documents/{document_id}"),
    ]:
        assert client.request(method, path, headers=other).status_code == 404
    assert client.get(f"/documents/{document_id}", headers=owner).status_code == 200


def test_endpoints_require_login():
    assert client.get("/documents").status_code == 401
    assert client.get("/documents/1").status_code == 401
    assert client.get("/documents/1/chunks").status_code == 401
    assert client.delete("/documents/1").status_code == 401
    assert client.post("/documents", files={"file": ("a.txt", b"hi", "text/plain")}).status_code == 401


def test_unsupported_empty_and_fake_files_are_rejected():
    headers = auth_headers("docs-reject@example.com")
    assert upload(headers, "program.exe", b"MZ binary").status_code == 415
    assert upload(headers, "empty.txt", b"").status_code == 422
    assert upload(headers, "fake.pdf", b"this is not a pdf").status_code == 422
    assert upload(headers, "binary.txt", b"abc\x00def").status_code == 422


def test_scanned_pdf_is_rejected_with_a_helpful_message(make_pdf):
    headers = auth_headers("docs-scan@example.com")
    response = upload(headers, "scan.pdf", make_pdf([""]), "application/pdf")
    assert response.status_code == 422
    assert "scanned" in response.json()["detail"]


def test_oversized_upload_is_rejected():
    headers = auth_headers("docs-big@example.com")
    assert upload(headers, "big.txt", b"a" * (1024 * 1024 + 1)).status_code == 413


def test_duplicate_upload_is_rejected_per_user():
    first = auth_headers("docs-dupe-1@example.com")
    second = auth_headers("docs-dupe-2@example.com")
    content = b"The same notes uploaded twice."
    assert upload(first, "a.txt", content).status_code == 201
    assert upload(first, "b.txt", content).status_code == 409
    assert upload(second, "a.txt", content).status_code == 201


def test_document_limit_per_user():
    headers = auth_headers("docs-limit@example.com")
    for number in range(5):
        assert upload(headers, f"note{number}.txt", f"Note number {number}".encode()).status_code == 201
    response = upload(headers, "note6.txt", b"One note too many")
    assert response.status_code == 403
    assert "limit" in response.json()["detail"].lower()


def test_delete_removes_rows_and_file():
    headers = auth_headers("docs-delete@example.com")
    document_id = upload(headers, "gone.txt", b"This will be deleted soon.").json()["id"]
    with SessionLocal() as db:
        path = get_settings().uploads_dir / db.get(Document, document_id).storage_path
        assert db.scalar(select(func.count(Chunk.id)).where(Chunk.document_id == document_id)) > 0
    assert path.exists()

    assert client.delete(f"/documents/{document_id}", headers=headers).status_code == 204

    with SessionLocal() as db:
        assert db.get(Document, document_id) is None
        assert db.scalar(select(func.count(Chunk.id)).where(Chunk.document_id == document_id)) == 0
    assert not path.exists()
    assert client.get(f"/documents/{document_id}", headers=headers).status_code == 404


def test_filename_cannot_escape_the_uploads_folder():
    headers = auth_headers("docs-evil@example.com")
    body = upload(headers, "../../evil.txt", b"Harmless content with a hostile name.").json()
    assert body["filename"] == "evil.txt"
    with SessionLocal() as db:
        stored = db.get(Document, body["id"]).storage_path
    assert ".." not in stored and "evil" not in stored
    assert (get_settings().uploads_dir / stored).exists()


def test_chunk_listing_is_paginated():
    headers = auth_headers("docs-pages@example.com")
    text = " ".join(f"word{number}" for number in range(2000)).encode()
    document = upload(headers, "long.txt", text).json()
    assert document["chunk_count"] > 4
    url = f"/documents/{document['id']}/chunks"
    page = client.get(url, params={"limit": 2, "offset": 1}, headers=headers).json()
    assert [chunk["position"] for chunk in page] == [1, 2]
    assert client.get(url, params={"limit": 0}, headers=headers).status_code == 422