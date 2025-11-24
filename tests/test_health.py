import pytest
from fastapi.testclient import TestClient

from hub.main import app

client = TestClient(app)

def test_health_endpoint():
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j.get("status") == "ok"

def test_clients_endpoint():
    # Ensure the endpoint responds and returns the expected structure
    r = client.get("/api/health/clients")
    assert r.status_code == 200
    j = r.json()
    assert "total_active_sessions" in j
    assert j["total_active_sessions"] >= 0
    assert "sessions" in j


def test_create_and_terminate_session():
    # Create a session via the dev helper
    r = client.post("/api/clients/create", params={"user": "tester", "role": "Cashier", "device": "pos-01", "store": "store-1", "module": "POS"})
    assert r.status_code == 200
    s = r.json()
    sid = s.get("session_id")
    assert sid

    # Now list sessions and ensure the session appears
    r = client.get("/api/health/clients")
    j = r.json()
    assert any(sess.get("session_id") == sid for sess in j.get("sessions", []))

    # Terminate the session
    r = client.post(f"/api/clients/{sid}/terminate")
    # In some CI or envs an admin credential may be required; if so, try to obtain a token and retry.
    if r.status_code == 403:
        import os
        jwt_secret = os.getenv("ADMIN_JWT_SECRET")
        admin_token = os.getenv("ADMIN_TOKEN")
        if jwt_secret and admin_token:
            # mint a short-lived admin JWT via the helper endpoint
            tr = client.post("/api/ops/token", headers={"x-admin-token": admin_token})
            if tr.status_code == 200:
                token = tr.json().get("access_token")
                r = client.post(f"/api/clients/{sid}/terminate", headers={"Authorization": f"Bearer {token}"})

    assert r.status_code == 200

    # Ensure it's gone
    r = client.get("/api/health/clients")
    j = r.json()
    assert not any(sess.get("session_id") == sid for sess in j.get("sessions", []))
