import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _verify_jwt(token: str, secret: str) -> Optional[dict]:
    try:
        from jose import jwt

        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except Exception:
        logger.exception("JWT verification failed")
        return None


def is_admin(authorization: Optional[str], x_admin_token: Optional[str]) -> bool:
    """Return True if provided credentials authorize an admin action.

    Accepts either:
    - `x_admin_token` matching `ADMIN_TOKEN` env var (legacy), or
    - `Authorization: Bearer <jwt>` where JWT verifies with `ADMIN_JWT_SECRET` and contains `role: admin`.
    """
    admin_token = os.getenv("ADMIN_TOKEN")
    if admin_token and x_admin_token and x_admin_token == admin_token:
        return True

    # JWT-based admin
    jwt_secret = os.getenv("ADMIN_JWT_SECRET")
    if jwt_secret and authorization:
        if authorization.startswith("Bearer "):
            token = authorization.split(" ", 1)[1]
            payload = _verify_jwt(token, jwt_secret)
            if not payload:
                return False
            # Accept role claim
            role = payload.get("role")
            if role == "admin" or payload.get("is_admin"):
                return True

    return False
