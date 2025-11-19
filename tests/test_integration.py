import os
import pytest

RUN_INTEGRATION = os.getenv("RUN_INTEGRATION") == "1"


@pytest.mark.skipif(not RUN_INTEGRATION, reason="Integration tests disabled")
def test_redis_session_store_integration():
    """Integration test for RedisSessionStore.

    Requires `REDIS_URL` environment variable (e.g. redis://localhost:6379/0)
    and a reachable Redis instance.
    """
    redis_url = os.getenv("REDIS_URL")
    assert redis_url, "REDIS_URL must be set for integration tests"

    from hub.session_store import RedisSessionStore

    store = RedisSessionStore(redis_url)

    # create
    s = store.create_session(user="int-test", role="Tester", device="ci")
    sid = s["session_id"]
    assert sid

    # get
    got = store.get_session(sid)
    assert got and got.get("user") == "int-test"

    # list contains
    lst = store.list_sessions()
    assert any(x.get("session_id") == sid for x in lst)

    # terminate
    ok = store.terminate_session(sid)
    assert ok is True

    # ensure removed
    assert store.get_session(sid) is None
