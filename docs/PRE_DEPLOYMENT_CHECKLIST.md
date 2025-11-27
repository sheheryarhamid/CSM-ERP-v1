# Pre-Deployment Checklist - Secure Blob Streaming v1.3.0

**Version:** 1.0  
**Date:** November 28, 2025  
**Feature:** Secure Blob Streaming with KMS Integration  
**Aligned with:** Central ERP Hub Master.ini Architecture

---

## Purpose

This checklist ensures all requirements from the Master.ini blueprint and blob streaming implementation are satisfied before staging or production deployment. It validates security, modularity, operational readiness, and Master.ini principle alignment.

---

## Section 1: Master.ini Principle Validation

### 1.1 Modular by Design ✓
- [ ] Blob streaming implemented as isolated module (no core Hub modifications)
- [ ] Feature can be disabled via configuration without breaking other modules
- [ ] Module manifest exists and declares dependencies/permissions
- [ ] Upgrade path documented (v1.2 → v1.3)

### 1.2 Security-First ✓
- [ ] AES-256-GCM encryption implemented and tested
- [ ] Key management follows Master.ini Section 📌6 requirements:
  - [ ] DPAPI support for Windows (dev/standalone)
  - [ ] KMS provider interface implemented (AWS/Azure/GCP)
  - [ ] Key rotation procedure documented
  - [ ] No plaintext keys in logs or error messages
- [ ] TLS enforcement configured for all endpoints
- [ ] Admin RBAC enforced on sensitive endpoints
- [ ] Audit logging active for all blob operations

### 1.3 Unified Data API Compliance ✓
- [ ] All blob endpoints use Hub authentication middleware
- [ ] JWT bearer tokens required (no anonymous access)
- [ ] Rate limiting configured per Master.ini defaults
- [ ] Endpoints exposed via OpenAPI spec
- [ ] Session tracking integrated with `session_store`

### 1.4 Offline-First Capability ✓
- [ ] LocalEncryptedBlobStore works without network (SQLite/filesystem)
- [ ] Sync mechanism ready for multi-store deployments
- [ ] Graceful degradation if Redis unavailable

### 1.5 Zero Vendor Lock-In ✓
- [ ] Blob storage abstraction supports multiple backends:
  - [ ] Local filesystem (dev/standalone)
  - [ ] S3-compatible (production, optional)
  - [ ] Azure Blob (production, optional)
- [ ] Export/migration tooling available
- [ ] No proprietary formats (standard AES-GCM + chunked format)

### 1.6 Growth Without Risk ✓
- [ ] Feature flag `ENABLE_BLOB_STREAMING` implemented
- [ ] Rollback procedure documented in `staging_deploy.md`
- [ ] Database migrations are reversible
- [ ] Previous version artifacts retained for emergency rollback

---

## Section 2: Security & Compliance (Master.ini Section 📌9)

### 2.1 Authentication & Authorization
- [ ] All endpoints require valid JWT or admin token
- [ ] Role checks: `Viewer` (read), `Manager` (write), `SuperAdmin` (delete)
- [ ] Session revocation tested (`/api/clients/{id}/terminate`)
- [ ] No hardcoded credentials in codebase

### 2.2 Encryption & Key Management
- [ ] Development: `BLOB_KEY` env var or DPAPI configured
- [ ] Staging: KMS provider configured and tested
- [ ] Production: KMS provider validated with cloud credentials
- [ ] Key rotation tested without downtime
- [ ] Encrypted data verified to be indistinguishable from random bytes

### 2.3 Audit Trail (Master.ini Section 🔐5)
- [ ] All blob operations logged to `hub:audit` (Redis) or `logs/audit.log`
- [ ] Log entries include: timestamp, user, action, blob_id, outcome
- [ ] Audit logs append-only and tamper-evident
- [ ] Retention policy configured (90 days minimum for compliance)
- [ ] Export mechanism tested (`/api/ops/audit`)

### 2.4 TLS & Transport Security
- [ ] TLS 1.2+ enforced for API endpoints
- [ ] SSL/TLS certificates valid and not self-signed (production)
- [ ] MySQL/PostgreSQL connections use SSL (`sslmode=require`)
- [ ] CSP headers configured to prevent XSS

### 2.5 Compliance Mapping
- [ ] **PCI-DSS**: No plaintext card data in blobs; encryption verified
- [ ] **GDPR**: PII redaction in logs; data export/delete endpoints ready
- [ ] **SOC 2**: Audit logs exportable; access controls documented
- [ ] **HIPAA** (if applicable): PHI encryption validated

---

## Section 3: Implementation Validation

### 3.1 Core Feature Verification
- [ ] Chunked blob upload tested (>100MB files)
- [ ] Streaming download tested (memory usage <20MB for any file size)
- [ ] HTTP Range support verified (RFC 7233 compliance)
- [ ] Pause/resume functionality tested
- [ ] Data integrity checks pass (uploaded SHA256 == downloaded SHA256)

### 3.2 Performance Benchmarks (from `dev/scripts/streaming_perf.py`)
- [ ] 100MB file streams in <5 seconds
- [ ] Throughput >30 MB/s for large files
- [ ] Memory usage <15MB for 100MB+ files
- [ ] Concurrent downloads tested (10+ simultaneous)
- [ ] No memory leaks after 1000+ operations

### 3.3 Error Handling
- [ ] Invalid blob_id returns 404 with safe error message
- [ ] Missing authentication returns 401 (not 500)
- [ ] Invalid Range header returns 416 Range Not Satisfiable
- [ ] Corrupted chunks detected and rejected
- [ ] KMS failures logged and surfaced appropriately

### 3.4 Frontend Integration (if using `secure-file-viewer.html`)
- [ ] UI displays real-time progress
- [ ] Pause/resume buttons functional
- [ ] Speed indicator accurate
- [ ] Activity log shows all API calls
- [ ] Download to browser works for various file types

---

## Section 4: Operational Readiness (Master.ini Section 📌11)

### 4.1 Monitoring & Observability
- [ ] Prometheus metrics exposed at `/metrics`:
  - [ ] `file_downloads_total` (counter)
  - [ ] `file_download_bytes_total` (counter)
  - [ ] `admin_operations_total` (counter)
  - [ ] `file_download_duration_seconds` (histogram)
- [ ] Grafana dashboard imported (from `production-rollout.md`)
- [ ] Alert rules configured:
  - [ ] High error rate (>5% for 5 minutes)
  - [ ] KMS failures (any failure triggers alert)
  - [ ] Blob store disk usage (>80%)
  - [ ] Audit log failures

### 4.2 Logging
- [ ] Structured JSON logs with fields: `timestamp`, `module`, `user`, `action`
- [ ] Log level configurable via `LOG_LEVEL` env var
- [ ] PII redacted from logs (no user emails/IPs)
- [ ] Logs centralized (ELK/Splunk/CloudWatch)
- [ ] Retention policy enforced (30 days application logs, 90 days audit logs)

### 4.3 Backup & Disaster Recovery (Master.ini Section 📌5)
- [ ] Backup includes encrypted blobs + metadata
- [ ] Backup encryption tested (AES-256)
- [ ] Restore procedure documented in `backup-and-drrunbook.md`
- [ ] Weekly automated restore test passing
- [ ] RTO: <4 hours, RPO: <1 hour validated

### 4.4 Health Checks
- [ ] `/health` endpoint returns 200 when healthy
- [ ] Health check includes:
  - [ ] Database connectivity
  - [ ] Blob store accessibility
  - [ ] KMS connectivity (production)
  - [ ] Redis connectivity (if enabled)
- [ ] Load balancer configured to poll health endpoint

---

## Section 5: KMS Integration (Production Only)

### 5.1 AWS KMS
- [ ] KMS key created with proper IAM policy
- [ ] Application IAM role has `kms:Decrypt`, `kms:Encrypt`, `kms:GenerateDataKey`
- [ ] Environment variables set:
  ```
  AWS_KMS_KEY_ID=arn:aws:kms:us-east-1:123456789012:key/xxx
  AWS_REGION=us-east-1
  ```
- [ ] `hub/kms_provider.py` tested with AWS credentials
- [ ] Key rotation tested (`aws kms enable-key-rotation`)

### 5.2 Azure Key Vault
- [ ] Key Vault created with RBAC permissions
- [ ] Service principal or managed identity configured
- [ ] Environment variables set:
  ```
  AZURE_KEY_VAULT_URL=https://mykeyvault.vault.azure.net/
  AZURE_KEY_NAME=erp-blob-encryption-key
  ```
- [ ] `hub/kms_provider.py` tested with Azure credentials
- [ ] Secret versioning verified

### 5.3 GCP KMS
- [ ] KMS keyring and key created
- [ ] Service account has `cloudkms.cryptoKeyVersions.useToEncrypt/Decrypt`
- [ ] Environment variables set:
  ```
  GCP_PROJECT_ID=my-project
  GCP_KEYRING=erp-hub-keyring
  GCP_KEY_NAME=blob-encryption-key
  GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json
  ```
- [ ] `hub/kms_provider.py` tested with GCP credentials
- [ ] Automatic rotation enabled (if desired)

### 5.4 KMS Provider Testing
- [ ] Run `python hub/kms_provider.py` for auto-detection test
- [ ] Verify 32-byte key retrieved successfully
- [ ] Test fallback to DPAPI/env if KMS unavailable (dev only)
- [ ] Test key rotation without service interruption
- [ ] Monitor KMS API call costs (should be <$10/month)

---

## Section 6: Staging Deployment (Prerequisites)

### 6.1 Infrastructure
- [ ] Staging server provisioned (VM or Kubernetes pod)
- [ ] Python 3.11+ installed
- [ ] Dependencies installed (`requirements.txt`)
- [ ] Encryption key configured (`BLOB_KEY` or KMS)
- [ ] Database accessible (MySQL/PostgreSQL/SQLite)

### 6.2 Deployment Artifacts
- [ ] Latest `main` branch pulled (commit: `5774e06` or later)
- [ ] All CI checks passing on GitHub
- [ ] Docker image built and pushed (if using containers)
- [ ] Configuration files deployed (`hub/.env` or ConfigMap)

### 6.3 E2E Validation (from `dev/runbooks/staging_deploy.md`)
Follow the 8 manual test cases:
1. [ ] **Blob Upload**: 10MB test file uploads successfully
2. [ ] **Blob List**: Uploaded blob appears in list
3. [ ] **Full Download**: Downloaded file matches original (SHA256)
4. [ ] **Range Request**: First half + second half = complete file
5. [ ] **UI Streaming**: `secure-file-viewer.html` shows progress/pause/resume
6. [ ] **Audit Log**: All operations logged with correct user/timestamp
7. [ ] **Metrics**: Prometheus queries return expected values
8. [ ] **Error Handling**: Invalid blob ID, token, auth tested

### 6.4 Performance Validation
- [ ] Latency: Small files <100ms, medium <1s, large <5s
- [ ] Throughput: >30 MB/s for large files
- [ ] Resource usage: <20% CPU, <20MB memory per download
- [ ] Concurrent load: 10+ simultaneous downloads without errors

---

## Section 7: Production Rollout (Prerequisites)

### 7.1 Phased Rollout Plan (from `docs/production-rollout.md`)
- [ ] **Phase 1 (Week 1)**: KMS setup complete (Section 5 above)
- [ ] **Phase 2 (Week 2)**: Application configuration verified
- [ ] **Phase 3 (Week 2)**: Monitoring dashboards deployed
- [ ] **Phase 4 (Week 3-4)**: Phased rollout 10%→25%→50%→100%
- [ ] **Phase 5 (Week 5+)**: Feature flag removal, cleanup

### 7.2 Feature Flag Configuration
- [ ] `ENABLE_BLOB_STREAMING=true` in production config
- [ ] Rollout percentage configurable (start at 10%)
- [ ] Fallback to legacy endpoints if flag disabled
- [ ] User segment targeting tested (internal users first)

### 7.3 Monitoring & Alerting
- [ ] PagerDuty/Opsgenie integration configured
- [ ] Alert escalation policy defined:
  - **P0**: KMS failure, data corruption (page immediately)
  - **P1**: High error rate, latency spike (page within 15 min)
  - **P2**: Storage capacity warning (email/Slack)
  - **P3**: Performance degradation (daily report)
- [ ] Runbook linked in alerts (incident response procedures)

### 7.4 Operational Procedures
- [ ] **Daily Ops**: Health check review, disk usage monitoring
- [ ] **Weekly**: Key rotation check, backup verification
- [ ] **Monthly**: Security review, compliance audit
- [ ] **Quarterly**: Disaster recovery drill, restore test

### 7.5 Incident Response
- [ ] Incident response playbook reviewed (`production-rollout.md` Section)
- [ ] On-call rotation defined
- [ ] Communication channels established (Slack/Teams)
- [ ] Rollback procedure tested (<5 minutes to previous version)

---

## Section 8: Documentation & Training

### 8.1 Documentation Completeness
- [ ] `docs/secure-blob-stream.md` reviewed and up-to-date
- [ ] `docs/production-rollout.md` validated against infrastructure
- [ ] `dev/runbooks/staging_deploy.md` tested end-to-end
- [ ] `dev/RELEASE_NOTES_v1.3.0.md` published to stakeholders
- [ ] OpenAPI spec updated with new endpoints

### 8.2 Team Training
- [ ] On-call team trained on blob streaming architecture
- [ ] Incident response procedures reviewed
- [ ] KMS key rotation procedure demonstrated
- [ ] Monitoring dashboard walkthrough completed
- [ ] Q&A session held with stakeholders

### 8.3 Change Management
- [ ] Deployment window scheduled (low-traffic period)
- [ ] Stakeholders notified (product, support, leadership)
- [ ] Customer communication prepared (if user-facing)
- [ ] Rollback decision criteria defined

---

## Section 9: Final Sign-Off

### 9.1 Security Review
- [ ] Security team sign-off obtained
- [ ] Vulnerability scan passed (no critical/high findings)
- [ ] Dependency audit clean (`pip-audit`)
- [ ] Code review approved (2+ reviewers)

### 9.2 Product Sign-Off
- [ ] Product owner approved feature completeness
- [ ] UX review passed (if UI components)
- [ ] Acceptance criteria met (all user stories closed)

### 9.3 Operations Sign-Off
- [ ] Operations team comfortable with runbooks
- [ ] Monitoring validated and tested
- [ ] Backup/restore procedure verified
- [ ] On-call team ready to support

### 9.4 Compliance Sign-Off
- [ ] Legal review passed (data handling policies)
- [ ] Compliance team approved (SOC 2/GDPR/PCI-DSS)
- [ ] Privacy team reviewed (PII handling)

---

## Section 10: Post-Deployment Validation

### 10.1 Smoke Tests (First 24 Hours)
- [ ] All health checks green
- [ ] No errors in logs for 1 hour
- [ ] Sample blob upload/download successful
- [ ] Monitoring dashboards showing expected metrics
- [ ] No alerts triggered

### 10.2 Performance Validation (First Week)
- [ ] P95 latency <2 seconds
- [ ] Error rate <0.5%
- [ ] Throughput meets SLA (>30 MB/s)
- [ ] No memory leaks detected
- [ ] KMS call volume within budget

### 10.3 User Feedback
- [ ] Internal users report no issues
- [ ] Support tickets reviewed (no major complaints)
- [ ] Beta users satisfied with performance
- [ ] Feature adoption tracking (usage metrics)

### 10.4 Cleanup
- [ ] Old mock endpoints deprecated (90-day notice)
- [ ] Legacy Redis keys removed (if migrated)
- [ ] Temporary feature flags removed (after 100% rollout)
- [ ] TODO tracking updated (archive planning docs)

---

## Appendix A: Quick Reference

### Environment Variables Summary
```bash
# Development
BLOB_KEY=<hex_key>                # Or use DPAPI
ADMIN_TOKEN=<secret>
ADMIN_JWT_SECRET=<secret>

# Production - AWS
AWS_KMS_KEY_ID=alias/erp-hub-blob-encryption
AWS_REGION=us-east-1

# Production - Azure
AZURE_KEY_VAULT_URL=https://vault.azure.net/
AZURE_KEY_NAME=erp-blob-key

# Production - GCP
GCP_PROJECT_ID=my-project
GCP_KEYRING=erp-keyring
GCP_KEY_NAME=blob-key
GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json

# Optional
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO
ENABLE_BLOB_STREAMING=true
```

### Key Commands
```powershell
# Run performance tests
python dev\scripts\streaming_perf.py

# Test KMS provider
python hub\kms_provider.py

# Deploy to staging
# Follow: dev\runbooks\staging_deploy.md

# Check health
Invoke-RestMethod http://staging:8000/health

# View metrics
Invoke-RestMethod http://staging:8000/metrics

# Audit logs
Invoke-RestMethod http://staging:8000/api/ops/audit `
  -Headers @{Authorization="Bearer $TOKEN"}
```

### Critical Paths
- **Runbooks**: `dev/runbooks/staging_deploy.md`
- **Production Guide**: `docs/production-rollout.md`
- **Incident Response**: `docs/production-rollout.md` (Section: Operational Procedures)
- **Master Principles**: `🏢 Central ERP Hub – The Official Master.ini`

---

## Checklist Status

**Overall Progress**: `_____ / _____ items complete`

**Sections Complete**:
- [ ] Section 1: Master.ini Validation
- [ ] Section 2: Security & Compliance
- [ ] Section 3: Implementation Validation
- [ ] Section 4: Operational Readiness
- [ ] Section 5: KMS Integration
- [ ] Section 6: Staging Deployment
- [ ] Section 7: Production Rollout
- [ ] Section 8: Documentation & Training
- [ ] Section 9: Final Sign-Off
- [ ] Section 10: Post-Deployment

**Approved By**:
- Security: _________________ Date: _________
- Product: _________________ Date: _________
- Operations: _________________ Date: _________
- Compliance: _________________ Date: _________

---

**Next Steps After Completion**:
1. Schedule deployment window
2. Execute staging deployment (Section 6)
3. Run E2E validation suite
4. Obtain final sign-offs (Section 9)
5. Execute production rollout (Section 7)
6. Monitor for 48 hours (Section 10)
7. Update TODO tracking → 100% complete

---

*This checklist aligns with Central ERP Hub Master.ini v1.3.0 principles and secure blob streaming v1.3.0 requirements.*
