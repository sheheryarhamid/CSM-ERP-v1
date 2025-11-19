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

    # Try Redis first (best-effort)
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            import redis

            client = redis.from_url(redis_url, decode_responses=True)
            client.rpush("hub:audit", json.dumps(event_copy))
            return
        except Exception:
            logger.exception("Failed writing audit to Redis; falling back to file")

    # Ensure logs dir exists
    try:
        os.makedirs("logs", exist_ok=True)
        path = os.path.join("logs", "audit.log")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event_copy, ensure_ascii=False) + "\n")
    except Exception:
        logger.exception("Failed writing audit to file")
