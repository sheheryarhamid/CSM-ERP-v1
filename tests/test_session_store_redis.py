import os
import pytest
from fastapi.testclient import TestClient

from hub.session_store import create_default_store


@pytest.mark.skipif(not os.getenv('REDIS_URL'), reason='REDIS_URL not set')
def test_redis_session_store_basic_lifecycle():
    store = create_default_store()
    # Must be Redis-backed for this test
    assert store is not None

    s = store.create_session(user='intuser', role='Viewer')
    sid = s['session_id']
    assert store.get_session(sid) is not None

    lst = store.list_sessions()
    assert any(item.get('session_id') == sid for item in lst)

    ok = store.terminate_session(sid)
    assert ok is True
    assert store.get_session(sid) is None
