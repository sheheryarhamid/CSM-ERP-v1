Title: chore: remove Redis runtime dependency and rate limiter (cleanup)

Summary
-------
This branch cleans up the runtime to remove the Redis dependency and the active rate-limiting behavior. The goals are:

- Remove the Redis-backed runtime features to make the hub self-contained for development.
- Remove active rate-limiting checks from `hub/main.py` and archive the limiter implementation.
- Simplify auditing to file-only (`logs/audit.log`) and avoid runtime Redis for audit events.
- Update docs and tests to reflect the simplified runtime. Redis integration tests are preserved but skipped and historical implementations remain in the backup branch.

Key changes in this branch
-------------------------

- `hub/main.py`: Removed runtime rate-limit enforcement; endpoint behavior remains otherwise unchanged.
- `hub/limiter.py`: Replaced with a placeholder to make accidental imports fail loudly; historical implementation preserved in history/backup.
- `hub/session_store_clean.py`: `create_default_store()` now returns `InMemorySessionStore` unconditionally to avoid runtime Redis.
- `hub/audit.py`: Audit now writes to `logs/audit.log` (file-only) and no longer attempts Redis writes at runtime.
- Tests: rate-limit behavior test skipped and Redis integration tests remain skipped unless `REDIS_URL` is set.
- Docs: `docs/limiter.md` and `docs/session_store.md` updated to mark the Redis-backed runtime features as archived and point to the backup branch for historical implementations.

Testing
-------

- Unit test suite (local): `py -3 -m pytest -q` — current result: `9 passed, 4 skipped` on my run after the cleanup.
- Frontend build: `npm ci && npm run build` — successful.

Notes
-----

- The original feature work (Redis-backed limiter and session store) is preserved in the backup branch `backup/feature/redis-limiter-sessionstore-20251120-000740` in case you want to restore or rework it later.

Files of interest
-----------------

- `hub/main.py`, `hub/limiter.py`, `hub/session_store_clean.py`, `hub/audit.py`
- `tests/test_rate_limit_and_metrics.py` (skipped rate-limit behavior)
- `docs/limiter.md`, `docs/session_store.md`

Next steps
----------

- Open a PR from `chore/cleanup-features` → `main` to merge these cleanup changes. I can open a PR for you or provide copy/paste content for the GitHub UI.
- Optionally delete the remote backup branch after you confirm it is no longer needed.

If you want me to open the PR, say "open PR" and I will prepare the PR title/body and attempt to open it (I may need your GitHub token or `gh` CLI configured to create the PR automatically). Otherwise I will provide the PR body for you to paste.
