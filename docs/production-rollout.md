# Production Rollout Guide - Secure Blob Streaming v1.3.0

## Executive Summary

This document outlines the production rollout plan for the Secure Blob Streaming feature (v1.3.0), including KMS integration, monitoring setup, and operational procedures.

**Target Date:** TBD  
**Feature Owner:** Security & Infrastructure Team  
**Rollout Type:** Phased deployment with feature flag

## Overview

### What's Being Deployed

- **Secure blob storage** with AES-256-GCM encryption
- **HTTP Range support** for resumable downloads
- **Cloud KMS integration** (AWS KMS, Azure Key Vault, or GCP KMS)
- **Enhanced monitoring** with Prometheus/Grafana dashboards
- **Audit logging** for compliance and security

### Business Value

- **Security:** End-to-end encrypted file storage
- **Reliability:** Resumable downloads for unstable connections
- **Scalability:** Memory-bounded streaming for files of any size
- **Compliance:** Audit trail for regulatory requirements

## Prerequisites

### Infrastructure
- [ ] Production Kubernetes cluster (v1.25+) OR VM-based deployment
- [ ] Cloud KMS service configured (AWS KMS / Azure Key Vault / GCP KMS)
- [ ] Prometheus + Grafana for monitoring
- [ ] Centralized logging (ELK, Splunk, or CloudWatch)
- [ ] Load balancer with TLS termination
- [ ] Object storage (S3, Azure Blob, or GCS) - optional for future enhancement

### Access & Permissions
- [ ] KMS key creation permissions
- [ ] IAM roles for application → KMS access
- [ ] Production deployment permissions
- [ ] Database admin access (for migrations)
- [ ] Monitoring dashboard admin access

### Documentation
- [ ] Staging validation complete (`dev/runbooks/staging_deploy.md`)
- [ ] Security review signed off
- [ ] Runbook training for on-call team
- [ ] Incident response procedures updated

## Phase 1: KMS Setup (Week 1)

### AWS KMS Configuration

#### 1.1 Create KMS Key

```bash
# Create KMS key for blob encryption
aws kms create-key \
  --description "ERP Hub Blob Encryption Key" \
  --key-usage ENCRYPT_DECRYPT \
  --origin AWS_KMS \
  --multi-region false \
  --tags TagKey=Environment,TagValue=Production TagKey=Service,TagValue=ERPHub

# Save key ID from output
export KMS_KEY_ID=<key_id>

# Create alias
aws kms create-alias \
  --alias-name alias/erp-hub-blob-encryption \
  --target-key-id $KMS_KEY_ID
```

#### 1.2 Configure IAM Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowBlobEncryptionKeyUsage",
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:Encrypt",
        "kms:GenerateDataKey",
        "kms:DescribeKey"
      ],
      "Resource": "arn:aws:kms:us-east-1:123456789012:key/${KMS_KEY_ID}"
    }
  ]
}
```

#### 1.3 Attach Policy to Application Role

```bash
# Create policy
aws iam create-policy \
  --policy-name ERPHubBlobEncryptionKMS \
  --policy-document file://kms-policy.json

# Attach to application role
aws iam attach-role-policy \
  --role-name ERPHubApplicationRole \
  --policy-arn arn:aws:iam::123456789012:policy/ERPHubBlobEncryptionKMS
```

#### 1.4 Implement KMS Provider

```python
# hub/key_provider.py (addition)

import boto3
from botocore.exceptions import ClientError

class AWSKMSKeyProvider:
    """AWS KMS-based key provider for production."""

    def __init__(self, key_id: str, region: str = "us-east-1"):
        self.key_id = key_id
        self.kms_client = boto3.client('kms', region_name=region)
        self._cache = None  # Cache data key

    def get_key(self) -> bytes:
        """Retrieve data encryption key from KMS."""
        if self._cache:
            return self._cache

        try:
            # Generate data key
            response = self.kms_client.generate_data_key(
                KeyId=self.key_id,
                KeySpec='AES_256'
            )
            
            # Cache plaintext key
            self._cache = response['Plaintext']
            
            # Store encrypted key for rotation
            self.encrypted_key = response['CiphertextBlob']
            
            return self._cache

        except ClientError as e:
            raise RuntimeError(f"KMS key retrieval failed: {e}")

    def rotate_key(self):
        """Force new data key generation."""
        self._cache = None
        return self.get_key()
```

### Azure Key Vault Configuration

#### 1.1 Create Key Vault

```bash
# Create resource group (if needed)
az group create --name erp-hub-prod --location eastus

# Create Key Vault
az keyvault create \
  --name erp-hub-blob-kv \
  --resource-group erp-hub-prod \
  --location eastus \
  --enable-rbac-authorization true

# Create key
az keyvault key create \
  --vault-name erp-hub-blob-kv \
  --name blob-encryption-key \
  --kty RSA \
  --size 2048 \
  --ops encrypt decrypt wrapKey unwrapKey
```

#### 1.2 Grant Access

```bash
# Get application managed identity
APP_IDENTITY=$(az webapp identity show \
  --name erp-hub-prod \
  --resource-group erp-hub-prod \
  --query principalId -o tsv)

# Grant key permissions
az keyvault set-policy \
  --name erp-hub-blob-kv \
  --object-id $APP_IDENTITY \
  --key-permissions get decrypt encrypt unwrapKey wrapKey
```

### GCP KMS Configuration

#### 1.1 Create Key Ring and Key

```bash
# Create key ring
gcloud kms keyrings create erp-hub-blob-keys \
  --location us-east1

# Create key
gcloud kms keys create blob-encryption-key \
  --location us-east1 \
  --keyring erp-hub-blob-keys \
  --purpose encryption

# Get key resource name
export KMS_KEY_NAME=projects/my-project/locations/us-east1/keyRings/erp-hub-blob-keys/cryptoKeys/blob-encryption-key
```

#### 1.2 Grant Service Account Access

```bash
# Grant encryption/decryption permissions
gcloud kms keys add-iam-policy-binding blob-encryption-key \
  --location us-east1 \
  --keyring erp-hub-blob-keys \
  --member serviceAccount:erp-hub@my-project.iam.gserviceaccount.com \
  --role roles/cloudkms.cryptoKeyEncrypterDecrypter
```

## Phase 2: Application Configuration (Week 2)

### 2.1 Update Environment Variables

```bash
# Kubernetes ConfigMap
kubectl create configmap erp-hub-config \
  --from-literal=KEY_PROVIDER=kms \
  --from-literal=KMS_KEY_ID=$KMS_KEY_ID \
  --from-literal=AWS_REGION=us-east-1 \
  --from-literal=BLOB_STORAGE_DIR=/mnt/blob-storage \
  --namespace production

# Or for Azure
kubectl create configmap erp-hub-config \
  --from-literal=KEY_PROVIDER=azure \
  --from-literal=AZURE_VAULT_URL=https://erp-hub-blob-kv.vault.azure.net \
  --from-literal=AZURE_KEY_NAME=blob-encryption-key \
  --namespace production
```

### 2.2 Deploy Application

```bash
# Build and push Docker image
docker build -t registry.example.com/erp-hub:v1.3.0 .
docker push registry.example.com/erp-hub:v1.3.0

# Update Kubernetes deployment
kubectl set image deployment/erp-hub \
  erp-hub=registry.example.com/erp-hub:v1.3.0 \
  --namespace production

# Or apply new manifest
kubectl apply -f k8s/production/deployment.yaml
```

### 2.3 Verify KMS Integration

```bash
# Exec into pod
kubectl exec -it deployment/erp-hub --namespace production -- /bin/bash

# Test KMS connectivity
python -c "
from hub.key_provider import get_key_bytes
key = get_key_bytes()
print(f'✓ KMS key retrieved: {len(key)} bytes')
"

# Expected output: "✓ KMS key retrieved: 32 bytes"
```

## Phase 3: Monitoring Setup (Week 2)

### 3.1 Prometheus Metrics

```yaml
# prometheus-rules.yaml
groups:
  - name: erp_hub_blob_streaming
    interval: 30s
    rules:
      # Error rate
      - record: erp_hub:blob_download:error_rate
        expr: |
          rate(file_downloads_total{status="error"}[5m]) /
          rate(file_downloads_total[5m])

      # Download throughput
      - record: erp_hub:blob_download:bytes_per_second
        expr: rate(file_download_bytes_total[5m])

      # P95 latency
      - record: erp_hub:blob_download:latency_p95
        expr: |
          histogram_quantile(0.95,
            rate(file_download_duration_seconds_bucket[5m])
          )

      # Active downloads
      - record: erp_hub:blob_download:active_count
        expr: sum(file_download_in_progress)

      # KMS call success rate
      - record: erp_hub:kms:success_rate
        expr: |
          rate(kms_calls_total{status="success"}[5m]) /
          rate(kms_calls_total[5m])
```

### 3.2 Grafana Dashboards

```json
{
  "dashboard": {
    "title": "ERP Hub - Secure Blob Streaming",
    "panels": [
      {
        "title": "Blob Downloads (Rate)",
        "targets": [{
          "expr": "rate(file_downloads_total[5m])"
        }],
        "type": "graph"
      },
      {
        "title": "Download Throughput",
        "targets": [{
          "expr": "erp_hub:blob_download:bytes_per_second"
        }],
        "type": "graph",
        "format": "Bps"
      },
      {
        "title": "Error Rate (%)",
        "targets": [{
          "expr": "erp_hub:blob_download:error_rate * 100"
        }],
        "type": "graph",
        "thresholds": [
          {"value": 1, "color": "yellow"},
          {"value": 5, "color": "red"}
        ]
      },
      {
        "title": "P95 Latency",
        "targets": [{
          "expr": "erp_hub:blob_download:latency_p95"
        }],
        "type": "graph",
        "thresholds": [
          {"value": 2, "color": "yellow"},
          {"value": 5, "color": "red"}
        ]
      },
      {
        "title": "KMS Health",
        "targets": [{
          "expr": "erp_hub:kms:success_rate * 100"
        }],
        "type": "singlestat",
        "thresholds": "90,95"
      }
    ]
  }
}
```

### 3.3 Alert Rules

```yaml
# alertmanager-rules.yaml
groups:
  - name: erp_hub_critical
    rules:
      - alert: BlobDownloadErrorRateHigh
        expr: erp_hub:blob_download:error_rate > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High blob download error rate"
          description: "{{ $value | humanizePercentage }} of downloads failing"

      - alert: KMSKeyRetrievalFailing
        expr: erp_hub:kms:success_rate < 0.95
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "KMS key retrieval failing"
          description: "KMS success rate: {{ $value | humanizePercentage }}"

      - alert: BlobDownloadLatencyHigh
        expr: erp_hub:blob_download:latency_p95 > 10
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow blob downloads"
          description: "P95 latency: {{ $value }}s"

      - alert: BlobStorageDiskFull
        expr: |
          (node_filesystem_avail_bytes{mountpoint="/mnt/blob-storage"} /
           node_filesystem_size_bytes{mountpoint="/mnt/blob-storage"}) < 0.15
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Blob storage disk space low"
          description: "{{ $value | humanizePercentage }} remaining"
```

## Phase 4: Phased Rollout (Week 3-4)

### 4.1 Feature Flag Configuration

```python
# hub/feature_flags.py

class FeatureFlags:
    """Feature flag management."""

    @staticmethod
    def is_secure_blob_enabled(user_id: str) -> bool:
        """Check if secure blob streaming is enabled for user."""
        # Phase 1: Internal users only
        if user_id in INTERNAL_USER_IDS:
            return True

        # Phase 2: Beta users (10%)
        if user_id in BETA_USER_IDS:
            return True

        # Phase 3: Gradual rollout
        rollout_percentage = get_rollout_percentage()
        return hash(user_id) % 100 < rollout_percentage

        # Phase 4: Full rollout
        # return True
```

### 4.2 Rollout Schedule

| Phase | Duration | Target Users | Success Criteria |
|-------|----------|--------------|------------------|
| **Phase 1: Internal** | Week 3 (Day 1-2) | Internal team (~10 users) | No errors, performance meets SLAs |
| **Phase 2: Beta** | Week 3 (Day 3-5) | Beta users (~100 users) | <1% error rate, positive feedback |
| **Phase 3: 25% Rollout** | Week 4 (Day 1-2) | 25% of production users | <1% error rate, no performance degradation |
| **Phase 4: 50% Rollout** | Week 4 (Day 3-4) | 50% of production users | Stable metrics, no incidents |
| **Phase 5: 100% Rollout** | Week 4 (Day 5-7) | All production users | Full deployment successful |

### 4.3 Rollout Checklist (Per Phase)

#### Before Rollout
- [ ] Previous phase metrics reviewed and acceptable
- [ ] No open P0/P1 incidents
- [ ] Monitoring dashboards verified
- [ ] On-call team briefed
- [ ] Rollback plan confirmed

#### During Rollout
- [ ] Increase feature flag percentage
- [ ] Monitor error rates for 1 hour
- [ ] Check dashboard metrics every 15 minutes
- [ ] Review logs for anomalies
- [ ] Verify KMS metrics stable

#### After Rollout
- [ ] No spike in error rates
- [ ] Performance metrics within SLAs
- [ ] User feedback collected (if applicable)
- [ ] Update rollout status
- [ ] Document any issues

### 4.4 Rollback Triggers

Immediate rollback if:
- Error rate > 5%
- P95 latency > 10s for 5+ minutes
- KMS success rate < 90%
- Critical security vulnerability discovered
- Data integrity issues detected

## Phase 5: Full Production (Week 5+)

### 5.1 Remove Feature Flag

Once 100% rollout stable for 7 days:

```python
# hub/feature_flags.py

class FeatureFlags:
    @staticmethod
    def is_secure_blob_enabled(user_id: str) -> bool:
        """Secure blob streaming fully enabled."""
        return True  # Feature flag removed
```

### 5.2 Deprecate Old Endpoints

```python
# hub/main.py

@app.get("/legacy/files/{file_id}")
@deprecated(version="1.3.0", reason="Use /secure/files/{blob_id}/stream")
async def legacy_download(file_id: str):
    """Deprecated: Use secure blob streaming instead."""
    raise HTTPException(
        status_code=410,
        detail="This endpoint is deprecated. Use /secure/files API."
    )
```

### 5.3 Cleanup

- Remove old blob storage format files (after backup)
- Archive deprecated code
- Update all client applications
- Remove feature flag code

## Operational Procedures

### Daily Operations

**Morning Check (30 min):**
1. Review overnight Grafana dashboard
2. Check alert history (any fires?)
3. Review error logs
4. Verify storage capacity
5. Check KMS metrics

**Weekly Review (1 hour):**
1. Performance trend analysis
2. Capacity planning review
3. Security audit log review
4. Cost analysis (KMS call volume)
5. Runbook updates

### Incident Response

#### Severity Levels

| Severity | Response Time | Example |
|----------|---------------|---------|
| P0 - Critical | 15 minutes | Complete service outage, data loss |
| P1 - High | 1 hour | KMS unavailable, high error rate |
| P2 - Medium | 4 hours | Degraded performance, partial outage |
| P3 - Low | 1 business day | Minor issues, feature requests |

#### P0 Incident Runbook

1. **Acknowledge** (2 min)
   - Page on-call engineer
   - Acknowledge in PagerDuty
   - Join incident bridge

2. **Assess** (5 min)
   - Check monitoring dashboards
   - Review recent deployments
   - Identify affected users/regions

3. **Mitigate** (10 min)
   - Rollback recent changes (if applicable)
   - Disable feature flag (revert to old behavior)
   - Scale up resources if needed
   - Enable fallback mechanisms

4. **Communicate** (5 min)
   - Update status page
   - Notify stakeholders
   - Post in incident channel

5. **Resolve** (variable)
   - Fix root cause
   - Deploy hotfix
   - Verify resolution
   - Re-enable feature

6. **Postmortem** (24-48 hours)
   - Write incident report
   - Identify action items
   - Update runbooks
   - Schedule team review

### Key Rotation

**Scheduled Rotation (Quarterly):**

```bash
# 1. Create new KMS key version
aws kms create-key-version --key-id $KMS_KEY_ID

# 2. Update application to use new version
kubectl set env deployment/erp-hub \
  KMS_KEY_VERSION=2 \
  --namespace production

# 3. Re-encrypt blobs (background job)
python scripts/reencrypt_blobs.py \
  --old-version 1 \
  --new-version 2 \
  --batch-size 100

# 4. Verify all blobs re-encrypted
python scripts/verify_encryption.py --version 2

# 5. Disable old key version (after 30 days)
aws kms disable-key --key-id $OLD_KEY_ID
```

## Cost Management

### KMS Cost Estimates

**AWS KMS Pricing (us-east-1):**
- Customer managed key: $1/month
- API requests: $0.03 per 10,000 requests

**Example:**
- 1,000,000 downloads/month
- 2 KMS calls per download (generate + decrypt)
- Total: 2,000,000 requests = $6/month + $1 key = **$7/month**

### Optimization Tips

1. **Cache data keys** - Reduce KMS API calls
2. **Batch operations** - Group key requests
3. **Use regional keys** - Avoid cross-region fees
4. **Monitor usage** - Set billing alerts

## Compliance & Security

### Audit Requirements

- **Logging:** All blob operations logged with actor, timestamp, action
- **Retention:** 7 years (per regulatory requirements)
- **Access:** Audit logs immutable, admin-only access
- **Encryption:** Audit logs encrypted at rest

### Security Checklist

- [ ] Encryption at rest (KMS)
- [ ] Encryption in transit (TLS 1.3)
- [ ] Admin authentication (JWT + RBAC)
- [ ] Audit logging enabled
- [ ] Monitoring alerts configured
- [ ] Incident response plan tested
- [ ] Disaster recovery procedures documented
- [ ] Security review completed
- [ ] Penetration test passed

### Compliance Standards

- **SOC 2 Type II:** Audit trail, access controls
- **HIPAA:** Encryption, audit logging, access restrictions
- **GDPR:** Data subject rights, deletion procedures
- **PCI DSS:** Encryption key management

## Success Metrics

### Technical Metrics
- **Availability:** >99.95% uptime
- **Error Rate:** <0.5%
- **P95 Latency:** <2 seconds
- **Throughput:** >30 MB/s per download

### Business Metrics
- **Adoption Rate:** >90% of file operations using secure blobs within 90 days
- **User Satisfaction:** >4.5/5 in feedback surveys
- **Cost:** <$100/month KMS costs
- **Security Incidents:** 0 encryption-related incidents

## Rollback Plan

If critical issues arise after full rollout:

### Immediate Rollback (15 minutes)

```bash
# 1. Disable feature flag
kubectl set env deployment/erp-hub \
  FEATURE_SECURE_BLOB_ENABLED=false \
  --namespace production

# 2. Verify old endpoints working
curl https://api.example.com/legacy/files/<file_id>

# 3. Monitor error rate decrease
```

### Full Rollback (1-2 hours)

```bash
# 1. Deploy previous version
kubectl set image deployment/erp-hub \
  erp-hub=registry.example.com/erp-hub:v1.2.0 \
  --namespace production

# 2. Remove KMS configuration
kubectl delete configmap erp-hub-config --namespace production

# 3. Restore database (if schema changed)
# Follow database rollback procedure

# 4. Verify system health
curl https://api.example.com/health
```

## Post-Launch

### Week 1 Review
- Analyze metrics vs. baseline
- Collect user feedback
- Identify quick wins
- Document lessons learned

### Month 1 Review
- Performance trend analysis
- Cost vs. budget review
- Security posture assessment
- Roadmap prioritization

### Quarterly Review
- Feature adoption metrics
- Business impact analysis
- Technical debt assessment
- Next phase planning

---

**Document Owner:** DevOps & Security Team  
**Approval Required:** VP Engineering, CISO  
**Last Updated:** 2025-11-28  
**Next Review:** Before production deployment
