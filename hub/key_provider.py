import os
import base64
from typing import Optional


class KeyProviderError(RuntimeError):
    pass


def _dpapi_unprotect(protected: bytes) -> bytes:
    """Use Windows DPAPI to unprotect bytes.

    This uses CryptUnprotectData via ctypes. Only available on Windows.
    """
    if os.name != 'nt':
        raise KeyProviderError("DPAPI is only supported on Windows")

    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.c_void_p)]

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    in_blob = DATA_BLOB()
    in_blob.cbData = len(protected)
    in_blob.pbData = ctypes.cast(ctypes.create_string_buffer(protected), ctypes.c_void_p)

    out_blob = DATA_BLOB()
    if not crypt32.CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)):
        raise KeyProviderError("CryptUnprotectData failed")

    try:
        buf = ctypes.cast(out_blob.pbData, ctypes.POINTER(ctypes.c_ubyte * out_blob.cbData)).contents
        return bytes(buf)
    finally:
        if out_blob.pbData:
            kernel32.LocalFree(out_blob.pbData)


def get_key_bytes(key_hex: Optional[str] = None) -> bytes:
    """Return AES key bytes.

    Selection logic:
    - If `key_hex` provided, use it.
    - If env `KEY_PROVIDER` == 'dpapi', attempt DPAPI providers:
      - `BLOB_KEY_DPAPI` (base64-encoded protected blob) or
      - `BLOB_KEY_DPAPI_FILE` (path to file containing protected blob)
    - Otherwise read `BLOB_KEY` from env as hex (legacy behavior).
    """
    # direct override
    if key_hex:
        try:
            key = bytes.fromhex(key_hex)
        except Exception:
            raise KeyProviderError("invalid BLOB_KEY hex")
        if len(key) not in (16, 24, 32):
            raise KeyProviderError("BLOB_KEY must be 16/24/32 bytes (hex)")
        return key

    provider = os.environ.get('KEY_PROVIDER', '').lower()
    if provider == 'dpapi':
        # prefer in-memory base64 protected blob
        b64 = os.environ.get('BLOB_KEY_DPAPI')
        path = os.environ.get('BLOB_KEY_DPAPI_FILE')
        if not b64 and not path:
            raise KeyProviderError('DPAPI configured but no protected blob found')
        if b64:
            try:
                protected = base64.b64decode(b64)
            except Exception:
                raise KeyProviderError('invalid base64 in BLOB_KEY_DPAPI')
        else:
            try:
                with open(path, 'rb') as fh:
                    protected = fh.read()
            except Exception as e:
                raise KeyProviderError('unable to read BLOB_KEY_DPAPI_FILE') from e

        key = _dpapi_unprotect(protected)
        if len(key) not in (16, 24, 32):
            raise KeyProviderError('unprotected DPAPI key has invalid length')
        return key

    # default: read hex from env
    key_hex = os.environ.get('BLOB_KEY')
    if not key_hex:
        raise KeyProviderError('BLOB_KEY not configured')
    try:
        key = bytes.fromhex(key_hex)
    except Exception:
        raise KeyProviderError('invalid BLOB_KEY hex')
    if len(key) not in (16, 24, 32):
        raise KeyProviderError('BLOB_KEY must be 16/24/32 bytes (hex)')
    return key


def get_default_key_provider():
    return get_key_bytes
