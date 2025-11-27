import os
import shutil
import struct
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi.testclient import TestClient

# prepare environment
ROOT = Path(__file__).resolve().parents[1]
BLOBS = ROOT / "dev" / "blobs"
BLOBS.mkdir(parents=True, exist_ok=True)

# 32-byte key (hex)
KEY = b"0" * 32
KEY_HEX = KEY.hex()
os.environ["BLOB_KEY"] = KEY_HEX
# ADMIN token for auth
os.environ["ADMIN_TOKEN"] = "dev-admin-token"

aesgcm = AESGCM(bytes.fromhex(KEY_HEX))
store = None
try:
    from hub.blob_store import LocalEncryptedBlobStore

    store = LocalEncryptedBlobStore()
except Exception:
    store = None

# create an encrypted chunked blob for file-1
plaintext = b"this is a test backup content for file-1\n" * 100
if store:
    store.create_chunked_blob("file-1", plaintext, chunk_size=1024)
else:
    # fallback: write single-record format (nonce + ciphertext)
    nonce = os.urandom(12)
    ciphertext = AESGCM(bytes.fromhex(KEY_HEX)).encrypt(nonce, plaintext, None)
    with open(BLOBS / "file-1.blob", "wb") as fh:
        fh.write(nonce + struct.pack(">I", len(ciphertext)))
        fh.write(ciphertext)

from hub.main import app

client = TestClient(app)


def test_download_blob():
    # call download with legacy x-admin-token
    resp = client.get(
        "/api/secure/files/file-1/download", headers={"x-admin-token": "dev-admin-token"}
    )
    assert resp.status_code == 200
    data = resp.content
    assert b"test backup" in data


def teardown_module(module):
    # clean up blobs
    try:
        shutil.rmtree(BLOBS)
    except Exception:
        pass
