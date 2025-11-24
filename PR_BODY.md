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

How to open the PR locally (recommended)
----------------------------------------

# Using GitHub CLI (`gh`):
gh pr create --title "chore: remove Redis runtime dependency and rate limiter (cleanup)" --body-file PR_BODY.md --base main --head chore/cleanup-features --draft

# Using GitHub REST API (requires `GITHUB_TOKEN` in env):
# Run in PowerShell (replace owner/repo if different):
$body = Get-Content -Raw PR_BODY.md
$payload = @{"title"="chore: remove Redis runtime dependency and rate limiter (cleanup)"; "head"="chore/cleanup-features"; "base"="main"; "body"=$body} | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri "https://api.github.com/repos/sheheryarhamid/CSM-ERP-v1/pulls" -Method Post -Headers @{Authorization = "token $env:GITHUB_TOKEN"; Accept = "application/vnd.github.v3+json"} -Body $payload

PR suggestions
--------------
- Reviewers: `@sheheryarhamid` (you) and any other core maintainers
- Labels: `chore`, `cleanup`

If you want me to open the PR for you, provide a GitHub token or confirm the `gh` CLI is authenticated and say "open PR".
