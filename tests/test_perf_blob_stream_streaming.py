import os
import time
import pytest
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Streaming performance test that avoids allocating the full payload in RAM.
# It builds a chunked AES-GCM blob by writing encrypted chunks directly to the
# blob file. This lets us test very large sizes without exhausting memory.

from hub.blob_store import BASE_DIR


@pytest.mark.skipif(os.getenv("PERF_STREAM") != "1",
                    reason="Performance streaming tests are disabled by default. Set PERF_STREAM=1 to enable.")
def test_stream_large_blob_streaming(tmp_path):
    size_mb = int(os.getenv("PERF_SIZE_MB", "50"))
    blob_id = "perf-large-stream-1"
    chunk_size = 64 * 1024

    # Ensure blob dir
    blobs = Path(BASE_DIR)
    blobs.mkdir(parents=True, exist_ok=True)

    # Prepare AES key from env or default test key
    key_hex = os.environ.get('BLOB_KEY', '00' * 32)
    key = bytes.fromhex(key_hex)
    aesgcm = AESGCM(key)

    out_path = blobs / f"{blob_id}.blob"
    # Write encrypted blob by emitting deterministic zero-chunks
    total_bytes = size_mb * 1024 * 1024
    written = 0
    with open(out_path, 'wb') as fh:
        while written < total_bytes:
            to_write = min(chunk_size, total_bytes - written)
            chunk = b"\x00" * to_write
            nonce = os.urandom(12)
            ciphertext = aesgcm.encrypt(nonce, chunk, None)
            fh.write(nonce)
            fh.write(len(ciphertext).to_bytes(4, 'big'))
            fh.write(ciphertext)
            written += to_write

    # Now stream using the existing blob store
    from hub.blob_store import LocalEncryptedBlobStore

    store = LocalEncryptedBlobStore()

    try:
        import psutil
        proc = psutil.Process()
        mem_before = proc.memory_info().rss
    except Exception:
        psutil = None
        mem_before = None

    bytes_read = 0
    start = time.time()
    for chunk in store.stream_blob(blob_id, chunk_size=chunk_size):
        bytes_read += len(chunk)
    duration = time.time() - start

    if psutil:
        mem_after = proc.memory_info().rss
        mem_delta = mem_after - mem_before
        assert mem_delta < 500 * 1024 * 1024, f"Memory increased too much: {mem_delta}"

    expected = total_bytes
    assert bytes_read == expected, f"expected {expected} bytes, got {bytes_read}"

    print(f"Streamed {bytes_read} bytes in {duration:.2f}s ({bytes_read/duration/1024/1024:.2f} MB/s)")
