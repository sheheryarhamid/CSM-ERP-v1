# Rate Limiter (Archived)

The runtime rate limiter and its Redis-backed variant have been removed in the cleanup branch.

Why archived

- To simplify the runtime and avoid an external Redis dependency in the mainline development branches, the team removed the active rate-limiting behavior. The hub now always allows terminate requests; this keeps the development experience simple and avoids flaky tests that depend on cross-process state.

If you need to reintroduce the limiter

- The original implementations and integration tests are preserved in the repository history and in the backup branch `backup/feature/redis-limiter-sessionstore-20251120-000740`.
- To reintroduce a limiter for multi-process deployments, implement a Redis-backed sliding-window approach or use a well-tested library and add CI integration to run Redis during integration tests.

Notes

- The codebase currently contains a placeholder module `hub/limiter.py` indicating removal. It will raise at import time if used; this is intentional to make accidental usage obvious during development.
