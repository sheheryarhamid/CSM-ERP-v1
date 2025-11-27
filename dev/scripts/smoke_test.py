from fastapi.testclient import TestClient

from hub.main import app


def run_smoke():
    c = TestClient(app)

    h = c.get("/health")
    print("GET /health ->", h.status_code, h.json())

    r = c.post("/api/clients/create", params={"user": "tester", "role": "Cashier"})
    print("POST /api/clients/create ->", r.status_code, r.json())

    docs = c.get("/docs")
    print("GET /docs ->", docs.status_code)


if __name__ == "__main__":
    run_smoke()
