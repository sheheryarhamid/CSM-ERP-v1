import os
import time

import pytest
from fastapi.testclient import TestClient

from hub.main import app


def test_terminate_rate_limit(monkeypatch, tmp_path):
    pytest.skip("Rate limiter removed in cleanup branch; skipping rate-limit behavior test")


def test_metrics_endpoint(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    r = client.get('/metrics')
    assert r.status_code == 200
    # should contain prometheus metrics header
    assert r.headers.get('content-type').startswith('text/plain')
