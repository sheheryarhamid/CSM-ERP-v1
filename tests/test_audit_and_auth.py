import json
import os
import time

from fastapi.testclient import TestClient

from hub.main import app


def _read_audit_file():
    path = os.path.join("logs", "audit.log")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as fh:
        return [json.loads(l) for l in fh.readlines() if l.strip()]


def test_admin_token_rbac(tmp_path, monkeypatch):
    # Ensure a clean audit log
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    # set legacy admin token
    monkeypatch.setenv("ADMIN_TOKEN", "secrettoken123")

    client = TestClient(app)

    # create session
    r = client.post("/api/clients/create", params={"user": "bob", "role": "Admin"})
    assert r.status_code == 200
    sid = r.json()["session_id"]

    # terminate without header -> 403
    r2 = client.post(f"/api/clients/{sid}/terminate")
    assert r2.status_code == 403

    # terminate with header -> 200
    r3 = client.post(f"/api/clients/{sid}/terminate", headers={"X-ADMIN-TOKEN": "secrettoken123"})
    assert r3.status_code == 200

    # audit file should contain an entry
    events = _read_audit_file()
    assert any(e.get("action") == "terminate_session" and e.get("session_id") == sid for e in events)


def test_jwt_admin_rbac(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # set JWT secret
    monkeypatch.setenv("ADMIN_JWT_SECRET", "jwtsecret")

    # create JWT
    import jwt

    token = jwt.encode({"role": "admin"}, "jwtsecret", algorithm="HS256")

    client = TestClient(app)
    r = client.post("/api/clients/create", params={"user": "alice", "role": "Admin"})
    assert r.status_code == 200
    sid = r.json()["session_id"]

    # terminate using Bearer token
    r2 = client.post(f"/api/clients/{sid}/terminate", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200

    # audit file should contain entry
    events = _read_audit_file()
    assert any(e.get("action") == "terminate_session" and e.get("session_id") == sid for e in events)


def test_mint_token_endpoint(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ADMIN_TOKEN", "legacy-token")
    monkeypatch.setenv("ADMIN_JWT_SECRET", "jwtsecret")

    client = TestClient(app)
    # request a token using legacy header
    r = client.post("/api/ops/token", headers={"X-ADMIN-TOKEN": "legacy-token"})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    token = body["access_token"]

    # use token to create and terminate a session
    r2 = client.post("/api/clients/create", params={"user": "minttest"})
    sid = r2.json()["session_id"]
    r3 = client.post(f"/api/clients/{sid}/terminate", headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 200
