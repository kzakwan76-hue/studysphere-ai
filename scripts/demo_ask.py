"""Ask a question about your uploaded documents.

1. Start the server:  cd backend, then  uvicorn app.main:app --reload
2. Upload the sample notes once:  python scripts\\demo_upload.py
3. Ask:  python scripts\\demo_ask.py "How many comparisons does binary search need?"
"""

import sys

import httpx

BASE_URL = "http://127.0.0.1:8000"
EMAIL = "demo@example.com"
PASSWORD = "demo-password-123"


def main() -> None:
    question = " ".join(sys.argv[1:]) or "How many comparisons does binary search need for a million sorted items?"
    try:
        with httpx.Client(base_url=BASE_URL, timeout=120) as client:
            login = client.post("/auth/login", data={"username": EMAIL, "password": PASSWORD})
            if login.status_code != 200:
                print("Login failed. Run scripts\\demo_upload.py first to create the demo account.")
                sys.exit(1)
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            response = client.post("/ask", json={"question": question}, headers=headers)
    except httpx.ConnectError:
        print("Could not reach the server. Start it first: cd backend, then uvicorn app.main:app --reload")
        sys.exit(1)

    body = response.json()
    if response.status_code != 200:
        print(f"Error {response.status_code}: {body.get('detail')}")
        sys.exit(1)
    print(f"Question: {question}\nStatus:   {body['status']}\n{body['message']}\n")
    if body["answer"]:
        print(body["answer"], "\n")
    for source in body["sources"]:
        mark = "cited" if source["cited"] else "     "
        print(f"[{source['number']}] {mark} {source['filename']} (page {source['page_number']}): {source['text'][:160]}...")
    for warning in body["warnings"]:
        print("Warning:", warning)


if __name__ == "__main__":
    main()