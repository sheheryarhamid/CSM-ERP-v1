import os
from typing import Iterator, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Simple local encrypted blob store implementation for dev/testing.
# Blobs are stored under `dev/blobs/` as raw bytes: 12-byte nonce + ciphertext.
# The encryption key is read from the environment variable `BLOB_KEY` (hex).

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dev", "blobs")


class BlobNotFound(Exception):
    pass


class LocalEncryptedBlobStore:
    def __init__(self, base_dir: Optional[str] = None, key_hex: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        key_hex = key_hex or os.environ.get("BLOB_KEY")
        if not key_hex:
            raise RuntimeError("BLOB_KEY not set for LocalEncryptedBlobStore")
        self.key = bytes.fromhex(key_hex)
        if len(self.key) not in (16, 24, 32):
            raise RuntimeError("BLOB_KEY must be 16/24/32 bytes (hex)")
        self.aesgcm = AESGCM(self.key)

    def _path_for(self, blob_id: str) -> str:
        # do not leak paths outside base_dir — sanitize blob_id
        safe = os.path.basename(blob_id)
        return os.path.join(self.base_dir, f"{safe}.blob")

    def list_blobs(self):
        if not os.path.isdir(self.base_dir):
            return []
        out = []
        for fn in os.listdir(self.base_dir):
            if fn.endswith('.blob'):
                out.append(fn[:-5])
        return out

    def get_meta(self, blob_id: str):
        p = self._path_for(blob_id)
        if not os.path.exists(p):
            raise BlobNotFound()
        st = os.stat(p)
        return {"id": blob_id, "size": st.st_size}

    def stream_blob(self, blob_id: str, chunk_size: int = 4096) -> Iterator[bytes]:
        """Stream decrypted blob bytes.

        File format: nonce (12 bytes) || ciphertext
        We decrypt the entire ciphertext as AESGCM expects the full ciphertext+tag.
        For demo/simplicity we read the ciphertext fully — for very large objects
        consider streaming-friendly envelope schemes.
        """
        p = self._path_for(blob_id)
        if not os.path.exists(p):
            raise BlobNotFound()
        with open(p, 'rb') as fh:
            nonce = fh.read(12)
            ciphertext = fh.read()
        # decrypt
        try:
            plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
        except Exception as e:
            raise RuntimeError("decryption failed") from e
        # yield in chunks
        idx = 0
        L = len(plaintext)
        while idx < L:
            end = min(idx + chunk_size, L)
            yield plaintext[idx:end]
            idx = end


def get_default_store() -> LocalEncryptedBlobStore:
    return LocalEncryptedBlobStore()
