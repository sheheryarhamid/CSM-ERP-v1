# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

- feat: add Redis-backed rate limiter with in-memory fallback (`hub/limiter.py`)
- feat: use Redis session store when `REDIS_URL` set (`hub/session_store.py`) + integration tests
- test: add `tests/test_limiter_redis.py` and `tests/test_session_store_redis.py` (skipped unless `REDIS_URL` set)
- ci: run Redis as a service in GitHub Actions integration job (`.github/workflows/ci.yml`)
- docs: add `docs/limiter.md` and `docs/session_store.md`
