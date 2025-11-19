import os
import pytest
import time
from fastapi.testclient import TestClient

from hub.main import app, limiter


@pytest.mark.skipif(not os.getenv('REDIS_URL'), reason='REDIS_URL not set')
def test_rate_limiter_redis_integration(tmp_path):
    # This test requires a running Redis instance specified by REDIS_URL
    client = TestClient(app)
    limiter.clear()
    os.environ['RATE_LIMIT_PER_MIN'] = '2'

    r = client.post('/api/clients/create', params={'user': 'redis-int'})
    assert r.status_code == 200
    sid = r.json()['session_id']

    r1 = client.post(f'/api/clients/{sid}/terminate')
    assert r1.status_code in (200, 404)

    r2 = client.post(f'/api/clients/{sid}/terminate')
    assert r2.status_code in (200, 404)

    r3 = client.post(f'/api/clients/{sid}/terminate')
    assert r3.status_code == 429
