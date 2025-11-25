# Performance streaming test

This folder contains an optional, local performance test for the secure blob streaming implementation.

How to run
- By design the test is skipped by pytest unless explicitly enabled. To run locally set:

```powershell
$env:PERF_STREAM = "1"
# optional: set size in MB (default 50)
$env:PERF_SIZE_MB = "100"
pytest -q tests/test_perf_blob_stream.py::test_stream_large_blob
```

Notes
- The test creates a chunked AES-GCM blob and streams it using the same server-side streaming helper used by the API.
- It allocates the test payload in memory before encrypting; keep `PERF_SIZE_MB` reasonable for your machine.
- If `psutil` is installed the test will run a best-effort RSS memory sanity check. If not installed the memory check is skipped.

Purpose
- Validate streaming throughput and ensure the streaming implementation yields bytes incrementally.
- Keep the test disabled by default to avoid heavy CI or developer machine impact.
