"""Secure-files API router providing safe metadata and streaming downloads.

Routes in this module intentionally avoid returning filesystem paths
to clients and enforce admin RBAC for download operations.
"""

"""Secure-files API router providing safe metadata and streaming downloads.

Routes in this module intentionally avoid returning filesystem paths
to clients and enforce admin RBAC for download operations.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Iterator

from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import StreamingResponse
from prometheus_client import Counter

from hub.auth import is_admin
from hub.audit import record_audit
from hub.blob_store import get_default_store, BlobNotFound
from hub.key_provider import KeyProviderError

router = APIRouter()

logger = logging.getLogger(__name__)

# Prometheus metrics (registered globally)
MET_FILE_DOWNLOADS = Counter('hub_file_downloads_total', 'Total file download requests')
MET_FILE_BYTES = Counter('hub_file_downloaded_bytes_total', 'Total bytes streamed for file downloads')
MET_FILE_DOWNLOAD_FAILURES = Counter('hub_file_download_failures_total', 'Failed file download attempts')

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


def _get_client_ip(request: Request) -> str:
    """Safely return client IP or 'unknown' when unavailable."""
    try:
        return (request.client and request.client.host) or 'unknown'
    except AttributeError as e:
        logger.debug("Unable to read client IP: %s", e)
        return 'unknown'


def _parse_range_header(range_header: str, total_size: int) -> tuple[int, int]:
    """Parse a simple bytes range header `bytes=<start>-<end>`.

    Returns (start, end) inclusive, or raises ValueError for invalid input.
    """
    if not range_header.startswith('bytes='):
        raise ValueError('unsupported range unit')
    rng = range_header[len('bytes='):].strip()
    if '-' not in rng:
        raise ValueError('invalid range')
    s, e = rng.split('-', 1)
    if s == '':
        # suffix range: last N bytes
        last_n = int(e)
        if last_n <= 0:
            raise ValueError('invalid range')
        start = max(0, total_size - last_n)
        end = total_size - 1
    else:
        start = int(s)
        end = int(e) if e != '' else total_size - 1

    if start < 0 or end < start or start >= total_size:
        raise ValueError('range not satisfiable')
    return start, end


def _make_counting_stream(inner_stream: Iterator[bytes]) -> Iterator[bytes]:
    try:
        for chunk in inner_stream:
            try:
                MET_FILE_BYTES.inc(len(chunk))
            except (TypeError, ValueError) as e:
                logger.debug("MET_FILE_BYTES.inc failed: %s", e)
            yield chunk
    except (RuntimeError, OSError) as e:
        MET_FILE_DOWNLOAD_FAILURES.inc()
        logger.exception("Error during streaming: %s", e)
        raise


def _make_ranged_stream(inner_stream: Iterator[bytes], start: int, end: int) -> Iterator[bytes]:
    sent = 0
    skipped = 0
    try:
        for chunk in inner_stream:
            if skipped + len(chunk) <= start:
                skipped += len(chunk)
                continue
            chunk_start = max(0, start - skipped)
            chunk_end = min(len(chunk), end - skipped + 1)
            to_send = chunk[chunk_start:chunk_end]
            if to_send:
                try:
                    MET_FILE_BYTES.inc(len(to_send))
                except (TypeError, ValueError) as e:
                    logger.debug("MET_FILE_BYTES.inc failed during ranged stream: %s", e)
                yield to_send
                sent += len(to_send)
            skipped += len(chunk)
            if skipped > end:
                break
    except (RuntimeError, OSError) as e:
        MET_FILE_DOWNLOAD_FAILURES.inc()
        logger.exception("Error during ranged streaming: %s", e)
        raise


@router.get("/secure/files")
async def list_files(request: Request):
    # require admin to list files in hardened mode
    auth = request.headers.get("authorization")
    x_admin = request.headers.get("x-admin-token")
    if not is_admin(auth, x_admin):
        raise HTTPException(status_code=403, detail="admin credentials required")

    # do not expose any filesystem paths; return safe metadata only
    out = []
    for f in _MOCK_FILES:
        out.append({
            "id": f["id"],
            "name": f["name"],
            "type": f["type"],
            "size_human": f.get("size_human"),
            "created_at": f.get("created_at"),
        })
    return out


@router.get("/secure/files/{file_id}/meta")
async def file_meta(file_id: str, request: Request):
    f = _find(file_id)
    if not f:
        raise HTTPException(status_code=404, detail="file not found")
    auth = request.headers.get("authorization")
    x_admin = request.headers.get("x-admin-token")
    if not is_admin(auth, x_admin):
        raise HTTPException(status_code=403, detail="admin credentials required")

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
    auth = request.headers.get("authorization")
    x_admin = request.headers.get("x-admin-token")
    if not is_admin(auth, x_admin):
        raise HTTPException(status_code=403, detail="admin credentials required")

    if f["type"] == "sqlite":
        preview = (
            "SQLite DB: tables=products,customers,sales — size approx "
            + f.get("size_human", "n/a")
        )
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
    client_ip = _get_client_ip(request)
    record_audit({
        "action": "file_download",
        "file_id": file_id,
        "by": actor,
        "client_ip": client_ip,
    })

    MET_FILE_DOWNLOADS.inc()

    try:
        store = get_default_store()
    except (ImportError, KeyError, RuntimeError, OSError, KeyProviderError) as e:
        logger.debug("get_default_store failed: %s", e)
        store = None

    if store is None:
        def iter_bytes():
            if f["type"] == "sqlite":
                yield b"-- SQLite meta: tables=products,customers,sales\n"
                yield (
                    b"-- This is a demo stream; real DB bytes should be "
                    b"streamed securely.\n"
                )
            elif f["type"] == "encrypted-backup":
                yield b"ENCRYPTED_BACKUP_HEADER\n"
                yield b"(binary blob omitted in demo)\n"
            else:
                yield b"(no data)\n"
        return StreamingResponse(iter_bytes(), media_type='application/octet-stream')

    try:
        inner_stream = store.stream_blob(f["id"])
    except BlobNotFound:
        MET_FILE_DOWNLOAD_FAILURES.inc()
        raise HTTPException(status_code=404, detail="file not found in blob store")
    except Exception as e:
        MET_FILE_DOWNLOAD_FAILURES.inc()
        logger.exception("Error reading blob: %s", e)
        raise HTTPException(status_code=500, detail="error reading blob")

    # Support HTTP Range header for resumable/partial downloads
    range_header = request.headers.get('range') or request.headers.get('Range')
    if not range_header:
        return StreamingResponse(_make_counting_stream(inner_stream), media_type='application/octet-stream')

    # Parse simple byte-range: bytes=<start>-<end?>
    try:
        total_size = store.get_plaintext_size(f['id'])
        start, end = _parse_range_header(range_header, total_size)
    except ValueError as e:
        # translate parsing/validation errors into HTTP responses
        logger.debug("Invalid Range header: %s", e)
        raise HTTPException(status_code=400, detail='invalid Range header')

    # Create a stream that skips until `start` and yields up to `end`.
    # create generator for the requested range
    content_length = end - start + 1
    headers = {
        'Content-Range': f'bytes {start}-{end}/{total_size}',
        'Accept-Ranges': 'bytes',
        'Content-Length': str(content_length),
    }
    return StreamingResponse(
        _make_ranged_stream(inner_stream, start, end),
        status_code=206,
        media_type='application/octet-stream',
        headers=headers,
    )
