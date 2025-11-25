# Secure Blob Stream — Operational Guide

This document explains the operational considerations for the secure blob streaming feature implemented in the Hub.

Contents
- Key providers (DPAPI, env, KMS placeholders)
- Blob format and streaming semantics
- Key rotation procedure (step-by-step)
- Backup & disaster recovery notes
- Troubleshooting

Improvements:
- Plaintext size sidecar: the blob store now writes a `.meta` sidecar file (`<blob>.meta`) containing JSON `{ "plaintext_size": <int> }` when blobs are created. This avoids an expensive decrypt-while-counting step for HTTP Range requests. If the sidecar is missing the store falls back to stream-decrypting to compute size.

Frontend memory note:
- The `SecureFileViewer` currently accumulates chunks in memory and assembles a `Blob` before triggering a client download. For very large files this may exhaust browser memory. Consider integrating `streamSaver.js` or writing to an IndexedDB-based writable stream to support truly large (>100MB) downloads without buffering the entire file in memory.

1. Key Providers

- DPAPI (Windows): The Hub supports a DPAPI-protected key payload provided via `BLOB_KEY_DPAPI` (base64) or `BLOB_KEY_DPAPI_FILE` (path to file). On Windows installations this is the recommended developer/installer mechanism for keeping the AES key off-disk in plaintext. The runtime uses CryptUnprotectData to unseal the key.

- Environment fallback: For simple deployments and CI, `BLOB_KEY` may be provided as a hex string environment variable. This is intended for dev/testing only and is less secure.

- KMS (placeholders): For production, store encryption keys in a cloud KMS or HSM (AWS KMS, Azure Key Vault, GCP KMS). The codebase includes an abstraction `hub/key_provider.py` — add a provider that calls your KMS and returns raw key bytes.

2. Blob Format & Streaming

- Format: chunked AES-GCM envelope. Each record is:
  - 12 bytes nonce
  - 4 byte big-endian ciphertext length
  - ciphertext+tag (len bytes)

- Streaming semantics: The server decrypts per-chunk and streams plaintext bytes to the client. The API endpoint `/api/secure/files/{id}/download` supports `Range` headers and returns `206 Partial Content` with `Content-Range` so clients can resume.

3. Key Rotation Procedure (zero-downtime recommended)

Goal: rotate the AES blob key without interrupting downloads or breaking access to existing blobs.

Minimal steps:

1. Generate new key material in KMS or with a secure RNG. Do NOT overwrite the old key yet.
2. Update the key provider to return the new key as the "primary" key while still accepting the old key as a secondary (the provider should expose both current and previous keys).
3. For newly written blobs: re-encrypt with the new key (update writers to use the primary key).
4. For existing blobs: support decryption with either the new key or the old key. The `blob_store` supports key-provider abstraction so it will try available keys in order.
5. After a monitoring window where all reads succeed with new key present, remove the old key from the provider and promote the new key as sole primary.

Best practices:
- Keep a key-version identifier with each blob’s metadata so you can quickly identify which key to try first.
- Audit key rotations and keep an immutable log of rotation events.

4. Backup & DR

- Never store raw key material in backups. Instead, store KMS key references or DPAPI-protected blobs which can be unsealed during restore.
- Regularly test restores to staging using your DR runbook.

5. Troubleshooting

- "Unable to decrypt blob": Ensure the key-provider is configured and that the key used to encrypt is present. Check `logs/audit.log` for rotation events.
- "Partial content/resume not working": Verify the server returns `Content-Range` and that the client sends `Range` header correctly. Use the provided performance test locally to validate behavior.

6. Next Steps / TODOs

- Implement cloud KMS providers in `hub/key_provider.py` (AWS/Azure/GCP). Add automated key-rotation tests.
- Add server-side watermarking/antivirus hooks for streamed blobs if required by policy.
