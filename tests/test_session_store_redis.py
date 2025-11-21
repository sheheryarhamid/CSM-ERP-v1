import pytest


def test_skipped_session_store_redis():
    pytest.skip("Redis integration tests disabled in cleanup branch")
