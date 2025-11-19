# Backup & Disaster Recovery Runbook

This runbook outlines the backup policy, procedures to create and restore backups, verification steps, and a weekly restore test to validate DR readiness.

Assumptions
- Backups are stored in an encrypted object store (S3-compatible or equivalent).
- Backups are signed to verify integrity.
- Secrets are managed separately (KMS). Backup archives include metadata for keys but not plaintext secrets.

Backup Policy
- Daily backups: retain 14 days
- Weekly backups: retain 12 weeks
- Monthly backups: retain 12 months
- All backups encrypted (AES-256) and signed (RSA/ECDSA)

Backup Contents
- Logical DB dump (schema + data)
- Module manifests and installed module list
- Configuration snapshots (env, feature flags)
- Key metadata (key ids, rotation history) — not secret material

Create Backup (manual)
1. Run `pg_dump` (Postgres) or `mysqldump` (MySQL) or export SQLite file
2. Export modules: `hub-cli export-manifests --output manifests.json`
3. Collect config: `hub-cli export-config --output config.json`
4. Package: `tar -czf backup-YYYYMMDD.tar.gz db_dump.sql manifests.json config.json`
5. Encrypt: `gpg --encrypt --recipient <backup-key> backup-YYYYMMDD.tar.gz`
6. Sign: `gpg --sign backup-YYYYMMDD.tar.gz.gpg`
7. Upload to storage and record metadata

Automated Backups
- Configure scheduled job (cron / cloud scheduler) that runs the same steps and uploads archives to object storage. Record results in monitoring and send alerts on failure.

Restore Procedure (high-level)
1. Provision a clean target environment (VM/container)
2. Fetch the backup archive and verify signature
3. Decrypt the archive
4. Restore config and manifests
5. Restore DB dump according to engine (Postgres/MySQL/SQLite)
6. Start Hub services and monitor logs for errors
7. Run smoke tests to validate expected endpoints and sample flows

Weekly Restore Test (automated)
- Schedule: weekly automatic restore into a staging environment
- Steps:
  - Pick the latest daily backup from last 7 days
  - Restore to staging environment
  - Run smoke tests (end-to-end: auth, module install, sample transaction)
  - Archive test results; if failed, open incident and notify owners

Validation & Monitoring
- Metric: `backup_success_total` and `backup_failure_total`
- Alert: any backup failure or failed restore test
- Store logs of backup and restore operations for audit review

RTO/RPO
- Default RTO: 4 hours (time to restore to operable state in staging)
- Default RPO: 1 hour (max acceptable data loss)
- Negotiate per customer and document in `ops/customer-{id}/dr-policy.md`

Notes
- For high-frequency deployments, consider WAL shipping and PITR for Postgres to reduce RPO.
- Regularly rotate encryption keys and test key rotation as part of restore tests.
