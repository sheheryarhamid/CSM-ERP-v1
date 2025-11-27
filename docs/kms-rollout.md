# KMS Rollout & Key Rotation Runbook

This document describes recommended approaches to integrate a cloud or on-prem KMS/HSM for blob encryption keys and a zero-downtime key rotation process.

1. Goals
- Use a managed KMS (AWS KMS, Azure Key Vault, GCP KMS) or HSM for root key material.
- Ensure per-deployment key access is logged and auditable.
- Support rolling key rotation with a two-key envelope strategy to avoid downtime.

2. Keying model
- Data keys (DEKs): AES-256 keys used to encrypt blobs. Stored encrypted with a KMS-wrapped key.
- Master key (KEK): Managed by KMS/HSM. Used only to wrap/unwrap DEKs.
- Envelope format: store metadata with each blob sidecar: {key_id, wrapped_dek, dek_version}

3. Migration path (DPAPI -> KMS)
- Step 0: Inventory
  - Identify blobs and their current key provider (DPAPI or env `BLOB_KEY`).
  - Export a list of affected blob IDs and sidecar metadata.
- Step 1: Introduce KMS DEK wrapping (dual-write read path)
  - On write: generate DEK locally, encrypt blob with DEK, wrap DEK with KMS (Get a wrapped blob) and store sidecar with wrapped_dek and `dek_version`.
  - On read: if sidecar indicates legacy (dpapi/env), unwrap using existing method; if `kms`-wrapped, call KMS to unwrap the DEK and decrypt.
- Step 2: Rewrap pass
  - Run a background job that reads each legacy-wrapped DEK, unwraps it, rewraps it with KMS, updates sidecar with `dek_version` and `key_id`.
  - Mark records as migrated in a migration table and retry failed operations.
- Step 3: Cutover
  - After migration completes and monitoring shows no errors, stop supporting legacy unwrap paths in code (feature flag first).

4. Rotation procedure (no downtime)
- Use key versioning in KMS.
- To rotate:
  1. Create new KEK in KMS (key version vN+1).
  2. For new writes, wrap with vN+1.
  3. Start background rewrap to re-encrypt DEKs using new KEK version.
  4. Monitor migration; once complete, revoke old KEK version if policy allows.

5. Access controls
- Use least-privilege IAM roles for any service that unwraps DEKs.
- Key usage should be limited to the minimal set of operations (Encrypt/Decrypt/Wrap/Unwrap) needed.

6. Audit & monitoring
- Enable KMS audit logs (CloudTrail / Azure Diagnostics / GCP Audit Logs).
- Emit application-level audit events when keys are wrapped/unwrapped.
- Alert on unwrap errors or unusual unwrap volumes.

7. Emergency rollback
- If FKMS is unavailable: fallback to DPAPI/env provider only if previously supported; otherwise block read and alert.
- Keep an exported, encrypted backup of DEKs (offline) before starting mass rewrap operations.

8. Operational checklist (pre-deploy)
- Ensure KMS keys exist and IAM policies are in place.
- Test wrap/unwrap with a staging dataset.
- Schedule background rewraps during off-peak windows.
- Backup current key metadata and record SHA256 of backup bundle.

9. Post-deploy verification
- Run a sampling job to decrypt random blobs and verify content.
- Validate audit logs show expected unwraps.

Appendix
- Example KMS call flow (AWS KMS) — pseudocode
  1. `generate_data_key(KeyId=KEK)` returns plaintext DEK + CiphertextBlob
  2. Encrypt chunk with plaintext DEK
  3. Store `CiphertextBlob` in sidecar
  4. On read: `decrypt(CiphertextBlob)` to retrieve DEK, then decrypt

