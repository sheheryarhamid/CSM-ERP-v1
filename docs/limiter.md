# Rate Limiter

This document describes the Hub's request rate-limiting behavior and configuration.

Environment variables

- `RATE_LIMIT_PER_MIN` — Number of allowed requests per minute per client IP to the `/api/clients/{session_id}/terminate` endpoint. Defaults to `60`.
- `REDIS_URL` — If set (e.g. `redis://localhost:6379/0`), the Hub will use Redis to maintain rate-limiter state across processes using a sorted-set per client. If not set or Redis not available, the Hub uses a thread-safe in-memory fallback suitable for single-process development servers.

Behavior

- The limiter implements a sliding-window algorithm with a 60-second window.
- When Redis is configured and reachable, the limiter uses a sorted set keyed by `rate:{client_ip}` and sets a TTL slightly longer than the window.
- The in-memory fallback stores timestamps in a per-client list and is cleared at process restart. Use Redis for multi-process/multi-host deployments.

Testing

- There is a skipped integration test template `tests/test_limiter_redis.py` that runs only when `REDIS_URL` is set. To run integration tests locally, start Redis and set `REDIS_URL`, for example:

```powershell
# Start redis (example using Docker)
docker run -d -p 6379:6379 --name hub-redis redis:7
$env:REDIS_URL = 'redis://127.0.0.1:6379/0'
py -3 -m pytest -q
```

Use this in CI when a runner provides Docker or a managed Redis instance.

CI (GitHub Actions)

The repository CI includes an `integration` job that starts Redis as a service and runs the Redis-backed limiter integration test. The job sets `REDIS_URL` to `redis://localhost:6379/0` so tests can connect to the service.

If you want to enable these integration tests locally, run Redis (via Docker or your platform package manager) and set `REDIS_URL` before running pytest.
