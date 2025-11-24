import os
from typing import Optional


class KeyProviderError(RuntimeError):
    pass


def get_key_bytes(key_hex: Optional[str] = None) -> bytes:
    """Return the AES key bytes used for blob encryption.

    By default this reads `BLOB_KEY` from the environment (hex-encoded).
    This function is a small abstraction so we can later plug in DPAPI
    (Windows), cloud KMS, or HSM providers.
    """
    key_hex = key_hex or os.environ.get("BLOB_KEY")
    if not key_hex:
        raise KeyProviderError("BLOB_KEY not configured")
    try:
        key = bytes.fromhex(key_hex)
    except Exception as e:
        raise KeyProviderError("invalid BLOB_KEY hex") from e
    if len(key) not in (16, 24, 32):
        raise KeyProviderError("BLOB_KEY must be 16/24/32 bytes (hex)")
    return key


def get_default_key_provider():
    """Return the default provider function for the app.

    Currently returns `get_key_bytes` but can be extended to return
    an object with richer behavior.
    """
    return get_key_bytes
