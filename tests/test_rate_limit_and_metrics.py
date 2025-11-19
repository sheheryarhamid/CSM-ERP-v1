import os
import time
from fastapi.testclient import TestClient

from hub.main import app


def test_terminate_rate_limit(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    # set a low rate limit
    monkeypatch.setenv('RATE_LIMIT_PER_MIN', '2')
    # Ensure limiter state is cleared between tests
    import hub.main as hub_main
    try:
        hub_main.limiter.clear()
    except Exception:
        pass
    client = TestClient(app)

    # create a session
    r = client.post('/api/clients/create', params={'user': 'rltest'})
    assert r.status_code == 200
    sid = r.json()['session_id']

    # first two attempts should work (no admin required by default)
    r1 = client.post(f'/api/clients/{sid}/terminate')
    assert r1.status_code in (200, 404)  # 404 if already removed

    # create another session to test limit more deterministically
    r = client.post('/api/clients/create', params={'user': 'rltest2'})
    sid2 = r.json()['session_id']
    r2 = client.post(f'/api/clients/{sid2}/terminate')
    # second attempt may be 200 or 404
    assert r2.status_code in (200, 404)

    # third immediate attempt should exceed limit
    r3 = client.post(f'/api/clients/{sid2}/terminate')
    assert r3.status_code == 429


def test_metrics_endpoint(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    r = client.get('/metrics')
    assert r.status_code == 200
    # should contain prometheus metrics header
    assert r.headers.get('content-type').startswith('text/plain')
