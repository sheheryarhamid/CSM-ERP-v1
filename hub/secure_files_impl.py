"""Secure-files API router providing safe metadata and streaming downloads.

Routes in this module intentionally avoid returning filesystem paths
to clients and enforce admin RBAC for download operations.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Iterator, Optional, Tuple

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from prometheus_client import Counter

from hub.audit import record_audit
from hub.auth import is_admin
from hub.blob_store import BlobNotFound, get_default_store
from hub.key_provider import KeyProviderError

router = APIRouter()

logger = logging.getLogger(__name__)

# Prometheus metrics (registered globally)
MET_FILE_DOWNLOADS = Counter("hub_file_downloads_total", "Total file download requests")
MET_FILE_BYTES = Counter(
    "hub_file_downloaded_bytes_total", "Total bytes streamed for file downloads"
)
MET_FILE_DOWNLOAD_FAILURES = Counter(
    "hub_file_download_failures_total", "Failed file download attempts"
)

# Keep the same mock registry so UI can discover files in dev
_NOW = datetime.now(timezone.utc).isoformat()

_MOCK_FILES = [
    {
        "id": "file-1",
        "name": "store-main.sqlite",
        "type": "sqlite",
        "size_human": "1.2 MB",
        "created_at": _NOW,
    },
    {
        "id": "file-2",
        "name": "backup-2025-11-20.enc",
        "type": "encrypted-backup",
        "size_human": "8.6 MB",
        "created_at": _NOW,
    },
]


def _find(file_id: str):
    """Return the mock file metadata dict for `file_id`, or None."""
    for f in _MOCK_FILES:
        if f["id"] == file_id:
            return f
    return None


def _get_client_ip(request: Request) -> str:
    """Safely return client IP or 'unknown' when unavailable."""
    try:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",", 1)[0].strip()
        return (request.client and request.client.host) or "unknown"
    except AttributeError:
        return "unknown"


def _parse_range_header(range_header: str, total_size: int) -> Tuple[int, int]:
    """Parse a simple bytes range header `bytes=<start>-<end>`.

    Returns (start, end) inclusive, or raises ValueError for invalid input.
    """
    if not range_header.startswith("bytes="):
        raise ValueError("unsupported range unit")
    rng = range_header[len("bytes=") :].strip()
    if "-" not in rng:
        raise ValueError("invalid range")
    s, e = rng.split("-", 1)
    if s == "":
        # suffix range: last N bytes
        last_n = int(e)
        if last_n <= 0:
            raise ValueError("invalid range")
        start = max(0, total_size - last_n)
        end = total_size - 1
    else:
        start = int(s)
        end = int(e) if e != "" else total_size - 1

    if start < 0 or end < start or start >= total_size:
        raise ValueError("range not satisfiable")
    return start, end


def _make_counting_stream(inner_stream: Iterator[bytes]) -> Iterator[bytes]:
    """Wrap a stream generator and increment the download byte metric."""
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
    """Produce a byte-range from an underlying stream generator.

    This avoids materializing the whole stream in memory by slicing
    chunks as they arrive.
    """
    pos = 0
    remaining = end - start + 1
    try:
        for chunk in inner_stream:
            chunk_len = len(chunk)
            if pos + chunk_len <= start:
                pos += chunk_len
                continue
            s = max(0, start - pos)
            e = min(chunk_len, s + remaining)
            to_send = chunk[s:e]
            if to_send:
                try:
                    MET_FILE_BYTES.inc(len(to_send))
                except (TypeError, ValueError) as e:
                    logger.debug("MET_FILE_BYTES.inc failed during ranged stream: %s", e)
                yield to_send
                remaining -= len(to_send)
            pos += chunk_len
            if remaining <= 0:
                break
    except (RuntimeError, OSError) as e:
        MET_FILE_DOWNLOAD_FAILURES.inc()
        logger.exception("Error during ranged streaming: %s", e)
        raise


def _build_dummy_stream(f: dict) -> Iterator[bytes]:
    """Return a small demo stream when no blob store is available."""
    if f["type"] == "sqlite":
        yield b"-- SQLite meta: tables=products,customers,sales\n"
        yield b"-- This is a demo stream; real DB bytes should be streamed securely.\n"
    elif f["type"] == "encrypted-backup":
        yield b"ENCRYPTED_BACKUP_HEADER\n"
        yield b"(binary blob omitted in demo)\n"
    else:
        yield b"(no data)\n"


def _get_store_or_none() -> Optional[Any]:
    """Attempt to obtain the default blob store; return None on expected failures.

    This centralizes exception handling and keeps the request handler concise.
    """
    try:
        return get_default_store()
    except (ImportError, KeyError, RuntimeError, OSError, KeyProviderError) as e:
        logger.debug("get_default_store failed: %s", e)
        return None


def _open_inner_stream(store: Any, file_id: str) -> Iterator[bytes]:
    """Open a blob stream from `store`, translating store errors to HTTPExceptions.

    Raises HTTPException on not found or read errors.
    """
    try:
        return store.stream_blob(file_id)
    except BlobNotFound as exc:
        MET_FILE_DOWNLOAD_FAILURES.inc()
        raise HTTPException(status_code=404, detail="file not found in blob store") from exc
    except (RuntimeError, OSError) as exc:  # pragma: no cover - defensive
        MET_FILE_DOWNLOAD_FAILURES.inc()
        logger.exception("Error reading blob: %s", exc)
        raise HTTPException(status_code=500, detail="error reading blob") from exc


@router.get("/secure/files")
async def list_files(request: Request):
    """List available files (metadata only). Requires admin in hardened mode."""
    # require admin to list files in hardened mode
    auth = request.headers.get("authorization")
    x_admin = request.headers.get("x-admin-token")
    if not is_admin(auth, x_admin):
        raise HTTPException(status_code=403, detail="admin credentials required")

    # do not expose any filesystem paths; return safe metadata only
    out = []
    for f in _MOCK_FILES:
        out.append(
            {
                "id": f["id"],
                "name": f["name"],
                "type": f["type"],
                "size_human": f.get("size_human"),
                "created_at": f.get("created_at"),
            }
        )
    return out


@router.get("/secure/files/{file_id}/meta")
async def file_meta(file_id: str, request: Request):
    """Return metadata for a single file id (admin required)."""
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
    """Return a short human-readable preview for the given file id."""
    f = _find(file_id)
    if not f:
        raise HTTPException(status_code=404, detail="file not found")
    auth = request.headers.get("authorization")
    x_admin = request.headers.get("x-admin-token")
    if not is_admin(auth, x_admin):
        raise HTTPException(status_code=403, detail="admin credentials required")

    if f["type"] == "sqlite":
        preview = "SQLite DB: tables=products,customers,sales — size approx " + f.get(
            "size_human", "n/a"
        )
    elif f["type"] == "encrypted-backup":
        preview = "Encrypted backup — metadata only. Restore via Hub UI."
    else:
        preview = "No preview available for this file type"

    return {"preview": preview}


@router.get("/secure/files/{file_id}/download")
async def file_download(
    file_id: str,
    request: Request,
    authorization: Optional[str] = Header(None),
    x_admin_token: Optional[str] = Header(None),
):
    """Stream a secure file download with optional HTTP Range support."""
    # enforce admin RBAC for downloads
    if not is_admin(authorization, x_admin_token):
        raise HTTPException(status_code=403, detail="admin credentials required")

    f = _find(file_id)
    if not f:
        raise HTTPException(status_code=404, detail="file not found")

    # Audit the download attempt and increment metric
    record_audit(
        {
            "action": "file_download",
            "file_id": file_id,
            "by": "admin",
            "client_ip": _get_client_ip(request),
        }
    )

    MET_FILE_DOWNLOADS.inc()

    store = _get_store_or_none()
    if store is None:
        return StreamingResponse(_build_dummy_stream(f), media_type="application/octet-stream")

    inner_stream = _open_inner_stream(store, f["id"])

    # Support HTTP Range header for resumable/partial downloads
    range_header = request.headers.get("range") or request.headers.get("Range")
    if not range_header:
        return StreamingResponse(
            _make_counting_stream(inner_stream), media_type="application/octet-stream"
        )

    try:
        total_size = store.get_plaintext_size(f["id"])
        start, end = _parse_range_header(range_header, total_size)
    except ValueError as exc:
        logger.debug("Invalid Range header: %s", exc)
        raise HTTPException(status_code=400, detail="invalid Range header") from exc

    content_length = end - start + 1
    headers = {
        "Content-Range": f"bytes {start}-{end}/{total_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
    }

    return StreamingResponse(
        _make_ranged_stream(inner_stream, start, end),
        status_code=206,
        media_type="application/octet-stream",
        headers=headers,
    )
