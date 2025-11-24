# Secure Encrypted Blob Stream — Plan

This folder contains the initial plan and notes for implementing secure encrypted blob storage
and streaming downloads for database backups and protected files. The goal is to replace the
current mock streaming in `hub/secure_files.py` with a production-ready stream from an
encrypted blob store (local encrypted files, or cloud object storage with server-side encryption).

Goals
- Provide server-side streaming downloads that never expose filesystem paths
- Support encrypted-at-rest blobs and server-side decryption streaming
- Enforce RBAC and audit logging for every download
- Efficiently stream large backups without loading into memory

Initial tasks
1. Design the blob format and key management approach (DPAPI / KMS / local master key)
2. Implement `hub/blob_store.py` interface with methods: `list_blobs()`, `get_meta(id)`, `stream_blob(id)`
3. Integrate `blob_store` into `hub/secure_files.py` download endpoint and remove mock
4. Add integration tests for streaming (small sample encrypted blob) using TestClient
5. Update frontend `SecureFileViewer` to request streaming downloads via OAuth-protected endpoints

Branch: `feat/secure-blob-stream`

Notes
- Keep the download endpoint as a streaming response and write audit entries per chunk/connection
- Consider range requests for resumable download support
- Prefer AES-GCM envelope encryption and store metadata (nonce, tag) alongside blobs

Created by automation to start the next development work.
