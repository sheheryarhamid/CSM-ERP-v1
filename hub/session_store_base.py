"""Shared session store implementations.

This module provides the canonical in-memory session store used by both
`hub.session_store` and `hub.session_store_clean` to avoid duplicated code.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class SessionSpec:
    """Data holder describing the properties required to create a session."""
    user: str
    role: str
    device: Optional[str] = None
    store: Optional[str] = None
    module: Optional[str] = None
    connection_type: Optional[str] = None


def _spec_to_kwargs(spec: Any) -> Dict[str, Any]:
    """Normalize a session spec into a simple kwargs dict.

    Accepts a dict, an object with attributes, or a Pydantic model instance.
    """
    if spec is None:
        return {}
    if isinstance(spec, dict):
        return spec.copy()
    # Pydantic BaseModel or similar
    if hasattr(spec, "dict"):
        try:
            return {k: v for k, v in spec.dict().items() if v is not None}
        except (AttributeError, TypeError):
            # model.dict() raised unexpected error; fall back to attribute access
            pass
    # Fallback to attribute access
    keys = ("user", "role", "device", "store", "module", "connection_type")
    return {k: getattr(spec, k, None) for k in keys}


class InMemorySessionStore:
    """Lightweight in-memory session store for development and tests.

    This implementation intentionally keeps a simple dict of session data
    and is not intended for production scale.
    """

    def __init__(self) -> None:
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_session(self, spec: Any) -> Dict[str, Any]:
        """Create a session from a single spec (dict, dataclass, or model).

        This reduces the number of positional arguments and centralizes parsing.
        """
        kw = _spec_to_kwargs(spec)
        user = kw.get("user")
        role = kw.get("role")
        device = kw.get("device")
        store = kw.get("store")
        module = kw.get("module")
        connection_type = kw.get("connection_type")

        session_id = str(uuid.uuid4())
        now = self._now()
        s = {
            "session_id": session_id,
            "user": user,
            "role": role,
            "device": device,
            "store": store,
            "module": module,
            "connection_type": connection_type,
            "start_time": now,
            "last_activity": now,
        }
        self.sessions[session_id] = s
        return s

    def list_sessions(self, *, _since_seconds: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return all sessions; `_since_seconds` reserved for future filtering."""
        return list(self.sessions.values())

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return the session dict for `session_id`, or None if not found."""
        return self.sessions.get(session_id)

    def terminate_session(self, session_id: str) -> bool:
        """Terminate the session identified by `session_id` and return True when removed."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
