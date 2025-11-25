# Session Store

The Hub currently runs with an in-memory session store by default to keep development self-contained.

- `InMemorySessionStore`: a development-only, process-local store. Suitable for local testing and single-process servers. Data is lost on process restart.

Archived / removed

- The Redis-backed `RedisSessionStore` runtime selection was removed during cleanup to avoid a hard runtime dependency on Redis in mainline branches. Historical Redis-backed implementations and integration tests are preserved in the repository history and in the backup branch `backup/feature/redis-limiter-sessionstore-20251120-000740`.

Selection

- The factory `create_default_store()` in `hub/session_store_clean.py` now always returns an `InMemorySessionStore`.

Notes

- If you require a Redis-backed store for production, reintroduce `RedisSessionStore` from the backup branch or implement a new production-grade store. Add CI integration to run Redis during integration tests if you want to validate multi-process behavior automatically.
