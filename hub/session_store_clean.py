from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid
import os
import json
import logging

logger = logging.getLogger(__name__)


class InMemorySessionStore:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_session(self, user: str, role: str, device: Optional[str] = None, store: Optional[str] = None, module: Optional[str] = None, connection_type: Optional[str] = None) -> Dict[str, Any]:
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

    def list_sessions(self, *, since_seconds: Optional[int] = None) -> List[Dict[str, Any]]:
        # since_seconds unused for now; return all
        return list(self.sessions.values())

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.sessions.get(session_id)

    def terminate_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False


class RedisSessionStore:
    # Redis-backed session store removed from runtime by cleanup.
    # Office note: RedisSessionStore was intentionally removed to keep
    # the runtime self-contained (in-memory store) and avoid external
    # dependencies during this cleanup.


# Factory to pick backend (Redis or in-memory)
def create_default_store():
    # Always return the in-memory store for now.
    return InMemorySessionStore()
