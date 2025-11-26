"""Key provider helpers: DPAPI and env-based AES key retrieval.

Provides `get_key_bytes` that supports a DPAPI-protected blob or a hex
`BLOB_KEY` environment variable for development and migration testing.
"""

import base64
import binascii
import ctypes
import os
from ctypes import wintypes
from typing import Optional


class KeyProviderError(RuntimeError):
    """Raised for errors retrieving or decoding key material from providers."""


def _dpapi_unprotect(protected: bytes) -> bytes:
    """Use Windows DPAPI to unprotect bytes.

    This uses CryptUnprotectData via ctypes. Only available on Windows.
    """
    if os.name != "nt":
        raise KeyProviderError("DPAPI is only supported on Windows")

    # The DATA_BLOB structure names follow the Windows API; disable naming
    # warnings for this small interop type.
    # pylint: disable=invalid-name,attribute-defined-outside-init
    class DATA_BLOB(ctypes.Structure):
        """Windows DATA_BLOB structure used by CryptUnprotectData."""

        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.c_void_p)]

    # pylint: enable=invalid-name,attribute-defined-outside-init

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    in_blob = DATA_BLOB()
    in_blob.cbData = len(protected)
    # separate buffer creation to keep line lengths reasonable
    _buf = ctypes.create_string_buffer(protected)
    in_blob.pbData = ctypes.cast(_buf, ctypes.c_void_p)

    out_blob = DATA_BLOB()
    success = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
    )
    if not success:
        raise RuntimeError("DPAPI unprotect failed")

    try:
        buf_ptr = ctypes.cast(out_blob.pbData, ctypes.POINTER(ctypes.c_ubyte * out_blob.cbData))
        return bytes(buf_ptr.contents)
    finally:
        kernel32.LocalFree(out_blob.pbData)


def get_key_bytes(key_hex: Optional[str] = None) -> bytes:
    """Return AES key bytes.

    Selection logic:
    - If `key_hex` provided, use it.
    - If env `KEY_PROVIDER` == 'dpapi', attempt DPAPI providers:
        - `BLOB_KEY_DPAPI` (base64-encoded protected blob), or
        - `BLOB_KEY_DPAPI_FILE` (path to file containing protected blob).
    - Otherwise read `BLOB_KEY` from env as hex (legacy behavior).
    """
    # direct override
    if key_hex:
        try:
            key = bytes.fromhex(key_hex)
        except ValueError as e:
            raise KeyProviderError("invalid BLOB_KEY hex") from e
        if len(key) not in (16, 24, 32):
            raise KeyProviderError("BLOB_KEY must be 16/24/32 bytes (hex)")
        return key

    provider = os.environ.get("KEY_PROVIDER", "").lower()
    if provider == "dpapi":
        # prefer in-memory base64 protected blob
        b64 = os.environ.get("BLOB_KEY_DPAPI")
        path = os.environ.get("BLOB_KEY_DPAPI_FILE")
        if not b64 and not path:
            raise KeyProviderError("DPAPI configured but no protected blob found")
        if b64:
            try:
                protected = base64.b64decode(b64)
            except (binascii.Error, ValueError) as e:
                raise KeyProviderError("invalid base64 in BLOB_KEY_DPAPI") from e
        else:
            try:
                with open(path, "rb") as fh:
                    protected = fh.read()
            except OSError as e:
                raise KeyProviderError("unable to read BLOB_KEY_DPAPI_FILE") from e

        key = _dpapi_unprotect(protected)
        if len(key) not in (16, 24, 32):
            raise KeyProviderError("unprotected DPAPI key has invalid length")
        return key

    # default: read hex from env
    key_hex = os.environ.get("BLOB_KEY")
    if not key_hex:
        raise KeyProviderError("BLOB_KEY not configured")
    try:
        key = bytes.fromhex(key_hex)
    except ValueError as e:
        raise KeyProviderError("invalid BLOB_KEY hex") from e
    if len(key) not in (16, 24, 32):
        raise KeyProviderError("BLOB_KEY must be 16/24/32 bytes (hex)")
    return key


def get_default_key_provider():
    """Return the default key-provider callable (for DI/overrides)."""
    return get_key_bytes
