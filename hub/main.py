"""Application entrypoint and admin/dev helper routes for the Hub."""

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from jwt import PyJWTError
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from pydantic import BaseModel

from . import secure_files_impl as secure_files
from .audit import record_audit
from .auth import is_admin
from .session_store import create_default_store

# Metrics
MET_TERMINATE_ATTEMPTS = Counter("hub_terminate_attempts_total", "Terminate attempts")
MET_TERMINATE_SUCCESS = Counter("hub_terminate_success_total", "Terminate success")
MET_TERMINATE_DENIED = Counter("hub_terminate_denied_total", "Terminate denied (auth/rate)")
MET_AUDIT_EVENTS = Counter("hub_audit_events_total", "Audit events written")
MET_AUTH_FAILURES = Counter("hub_auth_failures_total", "Authentication failures")

RATE_WINDOW_SECONDS = 60


app = FastAPI(title="Central ERP Hub - Dev Skeleton")
"""Application entrypoint and admin/dev helper routes for the Hub."""

logger = logging.getLogger(__name__)

# include secure file API (mock/stub for UI testing)
app.include_router(secure_files.router, prefix="/api")

# Initialize session store
session_store = create_default_store()

# Development CORS: allow common local dev origins. Lock this down in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Session(BaseModel):
    """Model representing a client session returned by the dev helper."""
    session_id: str
    user: str
    role: str
    device: str | None = None
    store: str | None = None
    module: str | None = None
    connection_type: str | None = None
    start_time: datetime | None = None
    last_activity: datetime | None = None


class ClientCreate(BaseModel):
    """Payload model for client creation helper endpoint."""
    user: str = "anonymous"
    role: str = "Viewer"
    device: str | None = None
    store: str | None = None
    module: str | None = None
    connection_type: str | None = None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/health/clients")
async def clients():
    """Return current active session summary for development/testing."""
    # Mock data for the skeleton. Replace with real session registry in implementation.
    # Use timezone-aware UTC datetimes to avoid deprecation warnings.
    sessions = session_store.list_sessions()
    now = datetime.now(timezone.utc).isoformat()
    total_active_sessions = len(sessions)
    total_active_users = len({s.get("user") for s in sessions if s.get("user")})
    return {
        "total_active_sessions": total_active_sessions,
        "total_active_users": total_active_users,
        "last_refresh": now,
        "sessions": sessions,
    }


@app.post("/api/clients/create")
async def create_client(request: Request):
    """Dev helper: create a session (not for production).

    Accepts either a JSON body or query parameters for convenience in tests.
    """
    # Try to read JSON body if provided, otherwise fall back to query params
    body = {}
    try:
        body = await request.json()
    except (ValueError, TypeError):
        # not JSON or no body provided
        body = {}

    params = dict(request.query_params)
    merged = {**body, **params}
    payload = ClientCreate(**merged)

    # Pass the payload object directly to the store which accepts a single spec.
    s = session_store.create_session(payload)
    return s


@app.post("/api/clients/{session_id}/terminate")
async def terminate_client(session_id: str, request: Request):
    """Terminate a session (dev helper).

    Reads any admin credentials from request headers and enforces RBAC if configured.
    """
    # Enforce admin RBAC only if an admin mechanism is configured.
    admin_token = os.getenv("ADMIN_TOKEN")
    jwt_secret = os.getenv("ADMIN_JWT_SECRET")
    if admin_token or jwt_secret:
        auth_header = request.headers.get("authorization")
        x_admin = request.headers.get("x-admin-token")
        if not is_admin(auth_header, x_admin):
            raise HTTPException(status_code=403, detail="admin credentials required")

    # Metric: count terminate attempts
    MET_TERMINATE_ATTEMPTS.inc()

    ok = session_store.terminate_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="session not found")

    # Mark success
    MET_TERMINATE_SUCCESS.inc()

    # Audit the action (best-effort)
    try:
        record_audit({"action": "terminate_session", "session_id": session_id, "by": "admin"})
    except OSError as e:
        logger.debug("record_audit failed on terminate_client: %s", e)

    return {"status": "terminated", "session_id": session_id}


@app.get("/metrics")
async def metrics():
    """Expose Prometheus metrics."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/ops/audit")
async def get_audit(request: Request, limit: int = 100):
    """Return recent audit events. Tries Redis `hub:audit` list first, falls back to `logs/audit.log`.

    If `ADMIN_TOKEN` or `ADMIN_JWT_SECRET` is configured the endpoint requires admin credentials.
    """
    # Enforce admin RBAC if configured
    admin_token = os.getenv("ADMIN_TOKEN")
    jwt_secret = os.getenv("ADMIN_JWT_SECRET")
    if admin_token or jwt_secret:
        auth_header = request.headers.get("authorization")
        x_admin = request.headers.get("x-admin-token")
        if not is_admin(auth_header, x_admin):
            raise HTTPException(status_code=403, detail="admin credentials required")

    # Read audit events from file (file-only audit storage after cleanup)
    events = []
    path = os.path.join("logs", "audit.log")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()[-limit:]
            for ln in lines:
                try:
                    events.append(json.loads(ln))
                except json.JSONDecodeError as e:
                    logger.debug("Failed to parse audit line: %s", e)
                    events.append({"raw": ln.strip()})
        except OSError as e:
            logger.debug("Failed reading audit log file %s: %s", path, e)

    return {"events": events}


@app.post("/api/ops/token")
async def mint_admin_token(x_admin_token: str | None = Header(None)):
    """Mint a short-lived admin JWT when provided the legacy `ADMIN_TOKEN`.

    Requires `ADMIN_JWT_SECRET` to be set. This is a dev-friendly helper; replace
    with a proper auth server in production.
    """
    admin_token = os.getenv("ADMIN_TOKEN")
    jwt_secret = os.getenv("ADMIN_JWT_SECRET")

    if not jwt_secret:
        raise HTTPException(status_code=400, detail="ADMIN_JWT_SECRET not configured")

    if not admin_token or x_admin_token != admin_token:
        raise HTTPException(status_code=403, detail="invalid admin token")

    # create a token with role=admin
    try:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "admin",
            "role": "admin",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=30)).timestamp()),
        }
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")
        return {"access_token": token, "token_type": "bearer"}
    except PyJWTError as e:
        raise HTTPException(status_code=500, detail="token generation failed") from e
