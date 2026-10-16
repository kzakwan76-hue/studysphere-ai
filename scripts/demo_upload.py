"""Create the demo account (if needed) and upload the sample documents.

1. Start the server:  cd backend, then  uvicorn app.main:app --reload
2. From the project root, run:  python scripts\\demo_upload.py

Safe to run more than once: the account is reused, and the server decides what to do with repeat uploads.
"""

import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "sample_docs"
BASE_URL = "http://127.0.0.1:8000"
EMAIL = "demo@example.com"
PASSWORD = "demo-password-123"
ALLOWED = {".pdf", ".txt", ".md"}


def main() -> None:
    files = sorted(p for p in SAMPLE_DIR.iterdir() if p.suffix.lower() in ALLOWED) if SAMPLE_DIR.is_dir() else []
    if not files:
        print(f"No sample documents found in {SAMPLE_DIR}. Check that the sample_docs folder exists.")
        sys.exit(1)

    try:
        with httpx.Client(base_url=BASE_URL, timeout=60) as client:
            register = client.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})
            if register.status_code not in (200, 201, 400, 409):
                print(f"Registration failed ({register.status_code}): {register.text[:200]}")
                sys.exit(1)

            login = client.post("/auth/login", data={"username": EMAIL, "password": PASSWORD})
            if login.status_code != 200:
                print(f"Login failed ({login.status_code}): {login.text[:200]}")
                sys.exit(1)
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            for path in files:
                response = client.post(
                    "/documents",
                    files={"file": (path.name, path.read_bytes(), "application/octet-stream")},
                    headers=headers,
                )
                if response.status_code in (200, 201):
                    print(f"Uploaded {path.name}: {response.json().get('chunk_count', '?')} chunks")
                else:
                    detail = response.json().get("detail", response.text[:200]) if response.content else ""
                    print(f"Skipped  {path.name} ({response.status_code}): {detail}")
    except httpx.ConnectError:
        print("Could not reach the server. Start it first: cd backend, then uvicorn app.main:app --reload")
        sys.exit(1)

    print('\nDone. Now try: python scripts\\demo_ask.py "How many comparisons does binary search need?"')


if __name__ == "__main__":
    main()