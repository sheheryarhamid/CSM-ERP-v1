# Running the Dev Skeleton (local)

Prerequisites:
- Python 3.10+ installed and on PATH
- Node.js (LTS) and npm on PATH

Steps (PowerShell):

1) Create venv and install Python deps (or use the included `install-deps-fixed.ps1`):

```powershell
py -3 -m venv .\venv
. .\venv\Scripts\Activate.ps1
py -3 -m pip install --upgrade pip
py -3 -m pip install -r .\requirements.txt
```

2) Start the backend dev server (from repo root):

```powershell
# with venv activated (or using py -3)
py -3 -m uvicorn hub.main:app --reload --host 0.0.0.0 --port 8000
```

3) Start the frontend dev server (in a new shell):

```powershell
cd .\frontend
npm run dev
npm run dev
```

- The frontend in this skeleton expects `/health` and `/api/health/clients` to be reachable from the same host/port. For dev you can run the frontend with Vite's proxy or run both behind a local reverse proxy.
- To run tests:

py -3 -m pip install -r requirements.txt
py -3 -m pytest -q
Run full stack locally with Docker Compose (Redis + Postgres + app):

```powershell
# start the stack (Docker Desktop required)
docker compose up -d

# stop the stack
docker compose down
```

Notes:
- The `app` service mounts the repository and installs `requirements.txt` inside the container on start. If you prefer not to use Docker, start the backend locally with `py -3 -m uvicorn hub.main:app --reload --host 0.0.0.0 --port 8000` and set `REDIS_URL` in your shell when connecting to a running Redis instance.
py -3 -m pip install -r requirements.txt
py -3 -m pytest -q
```

Troubleshooting:
- If the frontend cannot access the backend due to CORS or different ports, either configure Vite proxy in `frontend/vite.config.js` or enable CORS in the FastAPI app for development by adding `fastapi.middleware.cors.CORSMiddleware`.
