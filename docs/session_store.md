# Session Store

The Hub supports two session store implementations:

- `InMemorySessionStore`: a development-only, process-local store. Suitable for local testing and single-process servers. Data is lost on process restart.
- `RedisSessionStore`: a Redis-backed store that persists session JSON blobs and a set of active session IDs. Use this for multi-process deployments and production.

Selection

- The factory `create_default_store()` in `hub/session_store.py` will return a `RedisSessionStore` when the `REDIS_URL` environment variable is set and Redis is reachable. Otherwise it falls back to `InMemorySessionStore`.

Configuration

- `REDIS_URL` — set to a Redis connection URL, e.g. `redis://127.0.0.1:6379/0`.

Notes

- The Redis store uses JSON blobs and a Redis set `hub:sessions` as an index. It's intentionally simple for the MVP; production deployments may want to store structured data or use TTLs/expirations depending on session lifecycle policies.
- A lightweight integration test `tests/test_session_store_redis.py` is included and runs only when `REDIS_URL` is set (CI runs Redis as a service for integration tests).
