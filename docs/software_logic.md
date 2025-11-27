# Software Logic & Architecture (summary)

This document summarizes the key design decisions and runtime logic for the Central ERP Hub relevant for engineering and ops.

## High-level overview
- Backend: FastAPI service in `hub/` exposing a Unified Data API, admin endpoints and module host interfaces.
- Frontend: React SPA in `frontend/` that consumes the API and admin endpoints.
- Storage: primary relational DB (SQLite for standalone/dev, Postgres for production). Encrypted blobs stored on disk with AES-GCM per-chunk (server-side encryption). Keys managed via provider abstraction (DPAPI on Windows or `BLOB_KEY` env for dev).
- Sessions: In-memory store by default; Redis optional via `REDIS_URL`.

## Secure blob streaming (implementation notes)
- Blobs are written as sequences of AES‑GCM records: `[nonce(12)][len(4 BE)][ciphertext+tag]` per record.
- `hub/blob_store.py` implements `create_chunked_blob`, `stream_blob` and `get_plaintext_size`.
- Server supports HTTP `Range` responses and resumable downloads. The plaintext size is computed by streaming-decrypt and summing chunk lengths.
- Key provider: `hub/key_provider.py` supports Windows DPAPI (`BLOB_KEY_DPAPI` / `BLOB_KEY_DPAPI_FILE`) and `BLOB_KEY` hex env fallback.

## Auth & RBAC
- Admins may be authorized via `ADMIN_TOKEN` (legacy) or JWT signed with `ADMIN_JWT_SECRET`.
- JWT verification uses `PyJWT`.

## Observability & Audit
- Audit: append-only JSON lines to `logs/audit.log` during dev; in production replace with proper audit store/stream.
- Metrics: `prometheus_client` counters instrumented in key flows (file downloads, bytes, failures).

## Production vs Dev considerations
- Production must use a proper KMS/HSM for key management. DPAPI and `BLOB_KEY` are for dev/migration only.
- Use a managed DB (Postgres) and external object store (S3 / Azure Blob) for large blobs in production.
- Enable TLS, set up secrets management and rotate keys regularly.

## Suggested next steps for ops
- Add a KMS adapter (AWS KMS / Azure Key Vault) to `hub/key_provider.py` and a migration tool to re-encrypt blobs.
- Replace file-backed audit with secured, append-only remote audit sink.
- Add an integration test that streams a large blob (>=100MiB) through the API and verifies low memory usage.

