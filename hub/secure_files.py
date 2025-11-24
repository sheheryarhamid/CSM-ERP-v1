from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
from typing import List, Optional

from .auth import is_admin
from .audit import record_audit

router = APIRouter()

# Mock in-memory file registry for local/dev testing. In production this should
# be replaced with actual secure storage references (encrypted blobs, object store,
# or database records). Crucially, values DO NOT include any filesystem paths.
_MOCK_FILES = [
    {
        "id": "file-1",
        "name": "store-main.sqlite",
        "type": "sqlite",
        "size_human": "1.2 MB",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "file-2",
        "name": "backup-2025-11-20.enc",
        "type": "encrypted-backup",
        "size_human": "8.6 MB",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
]


def _find(file_id: str):
    for f in _MOCK_FILES:
        if f["id"] == file_id:
            return f
    return None


@router.get("/secure/files")
async def list_files(request: Request):
    """Return a list of protected file metadata. No filesystem paths are returned."""
    # TODO: enforce RBAC based on request headers/session; dev mode returns all
    return _MOCK_FILES


@router.get("/secure/files/{file_id}/meta")
async def file_meta(file_id: str, request: Request):
    """Return metadata for a protected file. No server paths are revealed."""
    f = _find(file_id)
    if not f:
        raise HTTPException(status_code=404, detail="file not found")
    # Provide only safe, displayable metadata
    return {
        "id": f["id"],
        "name": f["name"],
        "type": f["type"],
        "size_human": f.get("size_human"),
        "created_at": f.get("created_at"),
    }


@router.get("/secure/files/{file_id}/preview")
async def file_preview(file_id: str, request: Request):
    """Return a small, sanitized preview for text-like files.

    The implementation must not return full file contents for large DB blobs
    and must never include server filesystem paths. Here we return small
    mock previews for demo/testing.
    """
    f = _find(file_id)
    if not f:
        raise HTTPException(status_code=404, detail="file not found")

    if f["type"] == "sqlite":
        preview = "SQLite DB: tables=products,customers,sales — size approx " + f.get("size_human", "n/a")
    elif f["type"] == "encrypted-backup":
        preview = "Encrypted backup — metadata only. Restore via Hub UI."
    else:
        preview = "No preview available for this file type"

    return {"preview": preview}


@router.get("/secure/files/{file_id}/download")
async def file_download(file_id: str, request: Request, authorization: Optional[str] = Header(None), x_admin_token: Optional[str] = Header(None)):
    """Secure download endpoint.

    Streams file content server-side. Requires admin credentials (legacy x-admin-token or admin JWT).
    This endpoint intentionally never exposes filesystem paths. In production this
    should stream from a secure object store or decrypt blobs on the server.
    """
    # enforce admin RBAC for downloads
    if not is_admin(authorization, x_admin_token):
        raise HTTPException(status_code=403, detail="admin credentials required")

    f = _find(file_id)
    if not f:
        raise HTTPException(status_code=404, detail="file not found")

    # Audit the download attempt
    actor = "admin"
    try:
        # try to extract subject from JWT if present
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ", 1)[1]
            # don't import jose at module import time; do lightweight extraction
            try:
                from jose import jwt
                jwt_secret = None
                # only decode without verification if secret missing; keep minimal
                # In our dev flow we won't decode here; keep actor as admin
            except Exception:
                pass
    except Exception:
        pass

    record_audit({
        "action": "file_download",
        "file_id": file_id,
        "by": actor,
    })

    # Produce a small mock stream. In production, stream actual file bytes here.
    def iter_bytes():
        if f["type"] == "sqlite":
            yield b"-- SQLite meta: tables=products,customers,sales\n"
            yield b"-- This is a demo stream; real DB bytes should be streamed securely.\n"
        elif f["type"] == "encrypted-backup":
            yield b"ENCRYPTED_BACKUP_HEADER\n"
            yield b"(binary blob omitted in demo)\n"
        else:
            yield b"(no data)\n"

    return StreamingResponse(iter_bytes(), media_type='application/octet-stream')
