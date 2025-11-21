import pytest


def test_skipped_limiter_redis():
    pytest.skip("Redis integration tests disabled in cleanup branch")
