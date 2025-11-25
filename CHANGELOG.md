# Changelog

All notable changes to this project will be documented in this file.

## [v1.3.0] - 2025-11-26
- Security: replaced `python-jose` with `PyJWT` to remove `python-ecdsa` transitive dependency (remediates CVE/GHSA timing issue).
- Security: pinned `brotli>=1.2.0` to address compression-related CVE.
- CI: added `security-pip-audit` workflow running `pip-audit` on PRs/pushes.
- CI: added `ci-tests` workflow to run unit tests and `pylint` on PRs/pushes.
- Feature: secure blob streaming, DPAPI key provider, and frontend streaming consumer (implementation on `feat/secure-blob-stream`).

Notes:
- See `docs/secure-blob-stream.md` for operational details and key-rotation guidance.
# Changelog

All notable changes to this project will be documented in this file.

## [1.3.0] - 2025-11-25
### Added
- Secure blob streaming with chunked AES-GCM envelope format and Range support.
- `hub/key_provider.py` with DPAPI provider and env fallback; KMS provider placeholders.
- Server-side streaming endpoint `/api/secure/files/{id}/download` with audit and Prometheus metrics.
- Frontend `SecureFileViewer` supports streamed downloads (Fetch + ReadableStream) with pause/resume.
- Optional performance test `tests/test_perf_blob_stream.py` (skipped by default) and `dev/perf/README.md`.
- Operational docs `docs/secure-blob-stream.md` covering key rotation and DR notes.

### Changed
- Runtime cleanup: removed active rate limiter; Redis runtime usage is optional and documented.
- Docker compose and implementation plan updated to mark Redis as optional for local dev.
- Legacy mock `hub/secure_files.py` replaced with a placeholder; production router `hub/secure_files_impl.py` is used.

### Fixed
- Tests: made session termination tests resilient to CI auth differences; updated blob streaming tests.

### Notes
- The feature branch `feat/secure-blob-stream` contains implementation and tests. Merge workflow: create PR, run CI, and schedule staging tests for large-file streaming.
# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

- chore: remove Redis runtime dependency and rate limiter (cleanup)

- docs: mark limiter and Redis-backed session store as archived; point to backup branch

