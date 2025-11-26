# Repository Structure & Categorization

This page categorizes files/folders as Production, Dev/Test, or Docs/Meta to help maintainers and to prepare a minimal production bundle.

**Production / Runtime (required for deploy)**
- `hub/` — backend FastAPI app, runtime utilities (session store, blob store, audit). Core production artifacts.
- `frontend/` — React SPA sources that build into static assets for serving.
- `api/` — API surface and OpenAPI artifacts (if present).

**Dev / Auxiliary (not required in production bundle)**
- `dev/` — performance scripts, PR drafts, runbooks, local perf harnesses, and experimental scripts.
- `.venv/`, `venv/`, `.pytest_cache/` — virtualenvs and cache (should not be in production bundle).
- `scripts/` — helper scripts (dev/CI helpers) — verify before including.
- `tests/` — unit/integration tests (keep for CI but not required at runtime).

**Docs & Ops**
- `docs/` — canonical docs, runbooks, and guides (move here for consolidation).
- `CHANGELOG.md`, `README_RUN.md` — operational docs (consolidate into `docs/`).

**Archive / Backups**
- `dev/backups/` — backup blobs or historical objects; move large binary file backups to external storage.

**Repository-clean bundle guidance**
- For a production release bundle, include only:
  - `hub/` (source), `frontend/dist` (built assets), and `docs/` (install/run instructions)
  - Exclude: `.venv`, `dev/`, `tests/`, `logs/`, and any large binary backups

**Next actions recommended**
- Move draft PR/notes to `dev/archive/`.
- Consolidate README and run instructions into `docs/user_guide.md` (done).
- Create a `packaging/` script that assembles only the production files into a `.tar.gz` for release.

