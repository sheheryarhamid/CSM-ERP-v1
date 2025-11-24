from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
from typing import Optional

from .auth import is_admin
from .audit import record_audit
from .blob_store import get_default_store, BlobNotFound

router = APIRouter()

# Keep the same mock registry so UI can discover files in dev
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
    return _MOCK_FILES


@router.get("/secure/files/{file_id}/meta")
async def file_meta(file_id: str, request: Request):
    f = _find(file_id)
    if not f:
        raise HTTPException(status_code=404, detail="file not found")
    return {
        "id": f["id"],
        "name": f["name"],
        "type": f["type"],
        "size_human": f.get("size_human"),
        "created_at": f.get("created_at"),
    }


@router.get("/secure/files/{file_id}/preview")
async def file_preview(file_id: str, request: Request):
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
    # enforce admin RBAC for downloads
    if not is_admin(authorization, x_admin_token):
        raise HTTPException(status_code=403, detail="admin credentials required")

    f = _find(file_id)
    if not f:
        raise HTTPException(status_code=404, detail="file not found")

    # Audit the download attempt
    actor = "admin"
    record_audit({
        "action": "file_download",
        "file_id": file_id,
        "by": actor,
    })

    try:
        store = get_default_store()
    except Exception:
        store = None

    if store is None:
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

    try:
        stream = store.stream_blob(f["id"])
    except BlobNotFound:
        raise HTTPException(status_code=404, detail="file not found in blob store")
    except Exception:
        raise HTTPException(status_code=500, detail="error reading blob")

    return StreamingResponse(stream, media_type='application/octet-stream')
