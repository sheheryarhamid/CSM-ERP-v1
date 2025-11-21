Title: feat: Redis-backed rate limiter + Redis session store integration

Summary
-------
This PR introduces production-ready rate-limiting and session-store options, plus tests and CI improvements:

- Add a `RateLimiter` (`hub/limiter.py`) that prefers Redis (when `REDIS_URL` is configured) and falls back to a thread-safe in-memory implementation.
- Wire the `RateLimiter` into the terminate endpoint (`POST /api/clients/{session_id}/terminate`) in `hub/main.py` and preserve Prometheus metrics instrumentation.
- Ensure the session store uses Redis when `REDIS_URL` is present via the existing factory in `hub/session_store.py`.
- Add integration tests for the Redis-backed limiter and session store: `tests/test_limiter_redis.py` and `tests/test_session_store_redis.py` (both skipped unless `REDIS_URL` is set).
- Add a docs page `docs/limiter.md` describing limiter behavior and CI notes, and `docs/session_store.md` describing store selection.
- Update CI workflow (`.github/workflows/ci.yml`) to run Redis as a service for integration tests so the Redis-backed tests can run in CI without docker-compose.
- Add `.gitignore` and basic repo initialization (this branch contains the initial commit for the workspace changes).

Why
---
Using Redis for rate-limiting and sessions ensures correct behavior across multi-process and multi-host deployments. The in-memory fallbacks remain available for local development and quick testing. Integration tests and CI support make deployments safer.

Testing
-------
- Unit test suite: `py -3 -m pytest -q` — all unit tests pass locally (`10 passed, 3 skipped` on my run). Integration tests are skipped locally unless `REDIS_URL` is set.
- To run integration tests locally:

```powershell
# Start Redis in Docker
docker run -d -p 6379:6379 --name hub-redis redis:7
$env:REDIS_URL = 'redis://127.0.0.1:6379/0'
py -3 -m pytest -q
```

CI notes
--------
The CI workflow now starts Redis as a GitHub Actions service and runs the Redis-specific integration tests (the job `integration` sets `REDIS_URL=redis://localhost:6379/0`).

Files of interest
-----------------
- `hub/limiter.py` — Redis-backed sorted-set limiter + in-memory fallback
- `hub/main.py` — termination endpoint now uses `limiter`
- `hub/session_store.py` — RedisSessionStore available and selected when `REDIS_URL` is set
- `tests/test_limiter_redis.py`, `tests/test_session_store_redis.py` — integration tests (skipped unless `REDIS_URL` present)
- `docs/limiter.md`, `docs/session_store.md` — documentation
- `.github/workflows/ci.yml` — CI integration job now runs Redis as a service

Next steps
----------
- Push the branch to your remote and open a PR: `git push -u origin feature/redis-limiter-sessionstore` then create a PR on GitHub.
- Optionally: enable the Redis integration tests in CI by running the `integration` job on `push` or `workflow_dispatch` (already configured).
- Consider adding session TTLs, cleanup jobs, or stronger identity/auth for limiter keys (e.g., per-session keys) in a follow-up.

If you want, I can prepare a short PR description message for the GitHub UI (copy/paste), or open a draft PR if you provide the remote URL and allow pushing.
