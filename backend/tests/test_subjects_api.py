from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
PASSWORD = "correct-horse-battery"
NOTES = b"Binary search halves the list at every step. It needs a sorted list."
BIOLOGY = b"Mitochondria produce energy for the cell through respiration."


def auth_headers(email: str) -> dict[str, str]:
    client.post("/auth/register", json={"email": email, "password": PASSWORD})
    response = client.post("/auth/login", data={"username": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def upload(headers: dict[str, str], name: str, data: bytes):
    return client.post("/documents", files={"file": (name, data, "text/plain")}, headers=headers)


def make_subject(headers: dict[str, str], name: str = "Algorithms") -> int:
    response = client.post("/subjects", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def assign(headers: dict[str, str], subject_id: int, document_id: int):
    return client.put(f"/subjects/{subject_id}/documents/{document_id}", headers=headers)


def dashboard(headers: dict[str, str]) -> dict:
    return client.get("/dashboard", headers=headers).json()


def test_a_subject_can_be_created_listed_and_deleted():
    headers = auth_headers("subj-basic@example.com")
    created = client.post("/subjects", json={"name": "  Data   Structures "}, headers=headers)
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Data Structures" and body["document_count"] == 0 and body["chunk_count"] == 0
    assert [s["name"] for s in client.get("/subjects", headers=headers).json()] == ["Data Structures"]
    assert client.delete(f"/subjects/{body['id']}", headers=headers).status_code == 204
    assert client.get("/subjects", headers=headers).json() == []


def test_duplicate_names_are_refused_but_other_users_can_reuse_them():
    headers = auth_headers("subj-dup@example.com")
    other = auth_headers("subj-dup-other@example.com")
    make_subject(headers, "Biology")
    assert client.post("/subjects", json={"name": "biology"}, headers=headers).status_code == 409
    make_subject(other, "Biology")


def test_blank_or_missing_names_are_rejected():
    headers = auth_headers("subj-blank@example.com")
    assert client.post("/subjects", json={"name": "   "}, headers=headers).status_code == 422
    assert client.post("/subjects", json={}, headers=headers).status_code == 422
    assert client.post("/subjects", json={"name": "x" * 81}, headers=headers).status_code == 422


def test_the_number_of_subjects_is_limited(monkeypatch):
    monkeypatch.setattr("app.api.subjects.MAX_SUBJECTS_PER_USER", 2)
    headers = auth_headers("subj-limit@example.com")
    make_subject(headers, "One")
    make_subject(headers, "Two")
    assert client.post("/subjects", json={"name": "Three"}, headers=headers).status_code == 403


def test_subjects_are_private():
    owner = auth_headers("subj-owner@example.com")
    other = auth_headers("subj-intruder@example.com")
    subject_id = make_subject(owner)
    document_id = upload(other, "mine.txt", NOTES).json()["id"]
    assert client.get("/subjects", headers=other).json() == []
    assert client.get(f"/subjects/{subject_id}/documents", headers=other).status_code == 404
    assert client.delete(f"/subjects/{subject_id}", headers=other).status_code == 404
    assert assign(other, subject_id, document_id).status_code == 404


def test_you_cannot_put_someone_elses_document_in_your_subject():
    owner = auth_headers("subj-doc-owner@example.com")
    other = auth_headers("subj-doc-other@example.com")
    owner_document = upload(owner, "owner.txt", NOTES).json()["id"]
    other_subject = make_subject(other)
    assert assign(other, other_subject, owner_document).status_code == 404


def test_documents_can_be_assigned_counted_and_removed():
    headers = auth_headers("subj-assign@example.com")
    document = upload(headers, "notes.txt", NOTES).json()
    subject_id = make_subject(headers)
    assert assign(headers, subject_id, document["id"]).status_code == 204

    in_subject = client.get(f"/subjects/{subject_id}/documents", headers=headers).json()
    assert [d["id"] for d in in_subject] == [document["id"]]
    subject = client.get("/subjects", headers=headers).json()[0]
    assert subject["document_count"] == 1 and subject["chunk_count"] == document["chunk_count"]
    board = dashboard(headers)
    assert board["document_count"] == 1 and board["unassigned_document_count"] == 0
    assert board["documents"][0]["subject_id"] == subject_id

    assert client.delete(f"/subjects/{subject_id}/documents/{document['id']}", headers=headers).status_code == 204
    assert dashboard(headers)["unassigned_document_count"] == 1


def test_assigning_to_another_subject_moves_the_document():
    headers = auth_headers("subj-move@example.com")
    document_id = upload(headers, "notes.txt", NOTES).json()["id"]
    first = make_subject(headers, "First")
    second = make_subject(headers, "Second")
    assign(headers, first, document_id)
    assert assign(headers, second, document_id).status_code == 204
    counts = {s["name"]: s["document_count"] for s in client.get("/subjects", headers=headers).json()}
    assert counts == {"First": 0, "Second": 1}


def test_deleting_a_subject_keeps_its_documents():
    headers = auth_headers("subj-keep@example.com")
    document_id = upload(headers, "notes.txt", NOTES).json()["id"]
    subject_id = make_subject(headers)
    assign(headers, subject_id, document_id)
    assert client.delete(f"/subjects/{subject_id}", headers=headers).status_code == 204
    assert client.get(f"/documents/{document_id}", headers=headers).status_code == 200
    board = dashboard(headers)
    assert board["documents"][0]["subject_id"] is None and board["unassigned_document_count"] == 1


def test_deleting_a_document_removes_it_from_its_subject():
    headers = auth_headers("subj-docdel@example.com")
    document_id = upload(headers, "notes.txt", NOTES).json()["id"]
    subject_id = make_subject(headers)
    assign(headers, subject_id, document_id)
    assert client.delete(f"/documents/{document_id}", headers=headers).status_code == 204
    assert client.get("/subjects", headers=headers).json()[0]["document_count"] == 0
    assert client.get(f"/subjects/{subject_id}/documents", headers=headers).json() == []


def test_the_dashboard_and_subjects_require_login():
    assert client.get("/dashboard").status_code == 401
    assert client.get("/subjects").status_code == 401
    assert client.post("/subjects", json={"name": "Nope"}).status_code == 401


def test_asking_within_a_subject_only_uses_that_subjects_documents():
    headers = auth_headers("subj-ask@example.com")
    algorithms_doc = upload(headers, "algo.txt", NOTES).json()["id"]
    biology_doc = upload(headers, "bio.txt", BIOLOGY).json()["id"]
    algorithms = make_subject(headers, "Algorithms")
    biology = make_subject(headers, "Biology")
    assign(headers, algorithms, algorithms_doc)
    assign(headers, biology, biology_doc)

    question = "How does binary search work?"
    inside = client.post("/ask", json={"question": question, "subject_id": algorithms}, headers=headers).json()
    assert inside["status"] == "passages_only"
    assert {source["filename"] for source in inside["sources"]} == {"algo.txt"}

    outside = client.post("/ask", json={"question": question, "subject_id": biology}, headers=headers).json()
    assert outside["status"] == "not_found" and outside["sources"] == []


def test_ask_rejects_both_scopes_and_other_peoples_subjects():
    owner = auth_headers("subj-ask-owner@example.com")
    other = auth_headers("subj-ask-other@example.com")
    subject_id = make_subject(owner)
    document_id = upload(owner, "notes.txt", NOTES).json()["id"]
    question = "How does binary search work?"
    both = {"question": question, "subject_id": subject_id, "document_id": document_id}
    assert client.post("/ask", json=both, headers=owner).status_code == 422
    assert client.post("/ask", json={"question": question, "subject_id": subject_id}, headers=other).status_code == 404