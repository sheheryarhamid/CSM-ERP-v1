import os
import time

import pytest

from hub.blob_store import LocalEncryptedBlobStore


@pytest.mark.skipif(
    os.getenv("PERF_STREAM") != "1",
    reason="Performance streaming tests are disabled by default. Set PERF_STREAM=1 to enable.",
)
def test_stream_large_blob(tmp_path):
    """Optional performance test: stream a large synthetic blob via the blob store.

    This test is skipped by default. To enable locally, set:
      PERF_STREAM=1
      PERF_SIZE_MB=100   # optional, defaults to 50 MB

    Notes:
    - The test writes a chunked AES-GCM blob using the same helper used elsewhere
      and then iterates `stream_blob(...)` to validate streaming behavior.
    - If `psutil` is installed the test will also assert that RSS didn't grow
      excessively during streaming (best-effort check).
    """

    size_mb = int(os.getenv("PERF_SIZE_MB", "50"))
    blob_id = "perf-large-1"

    # Create store (uses default dev store path used by the app)
    store = LocalEncryptedBlobStore()

    chunk_size = 64 * 1024

    # NOTE: the test will allocate the test payload in memory; keep this skipped
    # by default to avoid CI / host issues. When running locally you can bump
    # PERF_SIZE_MB as desired.
    data = b"\x00" * (size_mb * 1024 * 1024)

    # Create a chunked encrypted blob (helper used by other tests)
    store.create_chunked_blob(blob_id, data, chunk_size=chunk_size)

    # Best-effort memory check if psutil is available
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
        # Allow a generous delta but fail if the process_ram grew by >200MB
        assert mem_delta < 200 * 1024 * 1024, f"Memory increased too much: {mem_delta}"

    expected = size_mb * 1024 * 1024
    assert bytes_read == expected, f"expected {expected} bytes, got {bytes_read}"

    print(
        f"Streamed {bytes_read} bytes in {duration:.2f}s ({bytes_read/duration/1024/1024:.2f} MB/s)"
    )
