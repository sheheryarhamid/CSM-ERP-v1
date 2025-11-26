"""Audit utilities — append-only file-backed audit events for dev/staging.

This module provides a minimal, durable audit sink used during development
and for environments where external audit services are not configured.
"""

import os
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_audit(event: dict) -> None:
    """Record an audit event.

    Writes to Redis list `hub:audit` if `REDIS_URL` is set and redis is available.
    Falls back to appending JSON lines to `logs/audit.log`.
    """
    event_copy = dict(event)
    event_copy.setdefault("timestamp", _now_iso())

    # Persist audit events to a local append-only file. This avoids
    # external dependencies during cleanup and provides a durable
    # developer-friendly audit trail. In production, replace this
    # with a proper audit/store service.
    try:
        os.makedirs("logs", exist_ok=True)
        path = os.path.join("logs", "audit.log")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event_copy, ensure_ascii=False) + "\n")
    except OSError as e:
        logger.exception("Failed writing audit to file: %s", e)
