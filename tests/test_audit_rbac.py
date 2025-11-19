import os
from fastapi.testclient import TestClient

from hub.main import app


def test_audit_rbac_legacy_token(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ADMIN_TOKEN", "admintoken123")
    client = TestClient(app)

    # without header should be forbidden
    r = client.get("/api/ops/audit")
    assert r.status_code == 403

    # with X-ADMIN-TOKEN header should succeed returning JSON
    r2 = client.get("/api/ops/audit", headers={"X-ADMIN-TOKEN": "admintoken123"})
    assert r2.status_code == 200
    assert "events" in r2.json()


def test_audit_rbac_jwt(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ADMIN_TOKEN", "legacytoken")
    monkeypatch.setenv("ADMIN_JWT_SECRET", "jwtsecret")
    client = TestClient(app)

    # mint a token
    r = client.post("/api/ops/token", headers={"X-ADMIN-TOKEN": "legacytoken"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    # call audit with Bearer token
    r2 = client.get("/api/ops/audit", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert "events" in r2.json()
