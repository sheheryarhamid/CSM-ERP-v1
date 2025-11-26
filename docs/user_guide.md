# User Guide — Central ERP Hub (Dev)

This guide explains how to run the development skeleton, where to find key services, and quick operational notes for contributors.

## Quick start (development)

Prerequisites:
- Python 3.10+ (3.11 recommended)
- Node.js LTS + npm
- Docker Desktop (optional for full stack)

Setup (PowerShell):

```powershell
py -3 -m venv .\.venv
. .\.venv\Scripts\Activate.ps1
py -3 -m pip install --upgrade pip
py -3 -m pip install -r requirements.txt
```

Run backend (dev):

```powershell
py -3 -m uvicorn hub.main:app --reload --host 0.0.0.0 --port 8000
```

Run frontend (dev):

```powershell
cd frontend
npm ci
npm run dev
```

Run tests:

```powershell
py -3 -m pytest -q
```

Docker compose (optional full stack):

```powershell
docker compose up -d
# stop
docker compose down
```

## Environment variables useful in dev
- `BLOB_KEY` — hex AES key (dev fallback for encrypted blob store)
- `ADMIN_TOKEN` — legacy admin token for admin-only endpoints
- `ADMIN_JWT_SECRET` — JWT secret for admin RBAC
- `REDIS_URL` — optional (runtime uses in-memory by default)

## Where to look in the repo
- `hub/` — backend FastAPI app and runtime code (production artifact)
- `frontend/` — React SPA (production artifact)
- `docs/` — canonical docs, runbooks, and guides (production + ops)
- `dev/` — development-only scripts, performance harnesses, PR drafts, and runbooks
- `tests/` — unit and integration tests (CI)

## Notes for maintainers
- Runtime default uses in-memory session store; Redis support exists but is opt-in via `REDIS_URL`.
- Audit events are appended to `logs/audit.log` in the repo during development.
- Avoid committing large binary blobs; use `dev/backups` or external storage.

