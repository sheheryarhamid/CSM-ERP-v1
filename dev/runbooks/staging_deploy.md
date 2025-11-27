# Staging Deploy Runbook

This runbook documents the steps required to deploy the current `main` branch to staging and run E2E validations for secure blob streaming.

## Prerequisites

- A staging environment with credentials (service principal, SSH key, or GitHub App installation token)
- Access to staging database and object store (if applicable)
- `STAGING_DEPLOY_KEY` or service principal stored in your secret manager
- Encryption key configured (BLOB_KEY or DPAPI setup)
- Admin JWT token for E2E testing

## Pre-Deployment Checklist

- [ ] All CI checks passing on main branch
- [ ] PR #7 (Secure Blob Streaming) merged and verified
- [ ] Staging environment healthy (monitoring green)
- [ ] Database backup completed
- [ ] Rollback plan reviewed
- [ ] Stakeholders notified of deployment window

## Deployment Steps

### 1. Prepare Build

From repo root:
```powershell
# Switch to main and pull latest
git checkout main
git pull origin main

# Install Python dependencies
py -3 -m pip install -r requirements.txt

# Install frontend dependencies (if applicable)
cd frontend
npm ci
npm run build
cd ..
```

### 2. Deploy Backend

Example using SSH + systemd:
```powershell
# Copy artifacts to staging
scp -r ./hub user@staging:/srv/erp
scp requirements.txt user@staging:/srv/erp/

# SSH into staging and deploy
ssh user@staging << 'EOF'
cd /srv/erp
source .venv/bin/activate
pip install -r requirements.txt --upgrade
systemctl restart erp.service
EOF
```

Alternative using Docker:
```powershell
# Build and push image
docker build -t registry.example.com/erp-hub:v1.3.0 .
docker push registry.example.com/erp-hub:v1.3.0

# Deploy on staging
ssh user@staging << 'EOF'
docker pull registry.example.com/erp-hub:v1.3.0
docker stop erp-hub || true
docker rm erp-hub || true
docker run -d --name erp-hub \
  -p 8000:8000 \
  -e BLOB_KEY=$STAGING_BLOB_KEY \
  registry.example.com/erp-hub:v1.3.0
EOF
```

### 3. Configure Encryption Key

Ensure encryption key is set on staging:
```powershell
ssh user@staging << 'EOF'
# Option 1: Environment variable
echo "export BLOB_KEY=<hex_key>" >> /srv/erp/.env

# Option 2: DPAPI (Windows staging)
# Key should already be stored in DPAPI
echo "export KEY_PROVIDER=dpapi" >> /srv/erp/.env

# Verify key configuration
cd /srv/erp
source .venv/bin/activate
python -c "from hub.key_provider import get_key_bytes; print(f'Key length: {len(get_key_bytes())} bytes')"
EOF
```

### 4. Deploy Frontend

Upload `frontend/dist` to static hosting:
```powershell
# Example: Azure Static Web Apps
az staticwebapp deploy \
  --name erp-hub-staging \
  --resource-group staging \
  --app-location frontend/dist

# Example: S3 + CloudFront
aws s3 sync frontend/dist s3://erp-hub-staging/ --delete
aws cloudfront create-invalidation --distribution-id EDFDVBD6EXAMPLE --paths "/*"
```

### 5. Run Database Migrations

If schema changes are included:
```powershell
ssh user@staging << 'EOF'
cd /srv/erp
source .venv/bin/activate
python -m alembic upgrade head
EOF
```

### 6. Verify Service Health

```powershell
# Health check
curl https://staging.example.com/health

# Expected response:
# {"status": "ok", "version": "1.3.0"}

# Check metrics endpoint
curl https://staging.example.com/metrics

# Verify in Prometheus/Grafana
# - erp_hub_up == 1
# - No error spikes in logs
```

## E2E Validation

### Automated Tests

Run automated test suite against staging:
```powershell
# Set staging endpoint
$env:API_BASE_URL = "https://staging.example.com"
$env:ADMIN_TOKEN = "<staging_admin_jwt>"

# Run E2E tests
py -3 -m pytest tests/test_e2e_streaming.py -v

# Run performance benchmarks
py -3 dev/scripts/streaming_perf.py
```

### Manual Validation Checklist

#### 1. Blob Upload Test
```powershell
# Create test file (10MB)
python -c "import os; open('test_10mb.bin', 'wb').write(os.urandom(10*1024*1024))"

# Upload to staging
$token = "<admin_jwt>"
curl -X POST https://staging.example.com/secure/files/upload `
  -H "Authorization: Bearer $token" `
  -F "file=@test_10mb.bin"

# Save blob_id from response
```

#### 2. Blob List Test
```powershell
curl https://staging.example.com/secure/files `
  -H "Authorization: Bearer $token"

# Verify uploaded blob appears in list
```

#### 3. Full Download Test
```powershell
curl https://staging.example.com/secure/files/<blob_id>/stream `
  -H "Authorization: Bearer $token" `
  -o downloaded_full.bin

# Verify file integrity
$originalHash = (Get-FileHash test_10mb.bin).Hash
$downloadedHash = (Get-FileHash downloaded_full.bin).Hash
if ($originalHash -eq $downloadedHash) {
    Write-Host "✓ Full download integrity verified" -ForegroundColor Green
} else {
    Write-Host "✗ File integrity check failed" -ForegroundColor Red
}
```

#### 4. Range Request / Resume Test
```powershell
# Download first half
curl https://staging.example.com/secure/files/<blob_id>/stream `
  -H "Authorization: Bearer $token" `
  -H "Range: bytes=0-5242879" `
  -o downloaded_half.bin

# Verify partial download
$halfSize = (Get-Item downloaded_half.bin).Length
if ($halfSize -eq 5242880) {
    Write-Host "✓ Range request successful (5 MB)" -ForegroundColor Green
} else {
    Write-Host "✗ Range request failed" -ForegroundColor Red
}

# Resume download (second half)
curl https://staging.example.com/secure/files/<blob_id>/stream `
  -H "Authorization: Bearer $token" `
  -H "Range: bytes=5242880-" `
  -o downloaded_resume.bin

# Combine files
cat downloaded_half.bin,downloaded_resume.bin | Set-Content -Path downloaded_combined.bin -Encoding Byte

# Verify combined file integrity
$combinedHash = (Get-FileHash downloaded_combined.bin).Hash
if ($originalHash -eq $combinedHash) {
    Write-Host "✓ Resume download integrity verified" -ForegroundColor Green
} else {
    Write-Host "✗ Combined file integrity check failed" -ForegroundColor Red
}
```

#### 5. UI Streaming Test
1. Open `https://staging.example.com/secure-file-viewer` in browser
2. Enter staging admin JWT token
3. Enter blob ID from upload test
4. Click "Start Download"
5. Verify:
   - [ ] Progress bar updates smoothly
   - [ ] Speed indicator shows reasonable throughput
   - [ ] Downloaded bytes match total size at completion
   - [ ] File downloads to browser automatically
   - [ ] Downloaded file matches original (hash check)
6. Test pause/resume:
   - [ ] Click "Pause" mid-download
   - [ ] Progress stops
   - [ ] Click "Resume"
   - [ ] Download continues from same position
   - [ ] Final file is complete and valid

#### 6. Audit Log Verification
```powershell
# SSH to staging and check audit logs
ssh user@staging << 'EOF'
cd /srv/erp
tail -100 logs/audit.log | grep "blob_download"
EOF

# Verify entries contain:
# - Timestamp
# - Actor (admin username)
# - blob_id
# - IP address
# - Status (success)
# - Bytes transferred
```

#### 7. Metrics Verification
```powershell
# Query Prometheus on staging
curl 'https://prometheus.staging.example.com/api/v1/query?query=file_downloads_total'

# Verify metrics increased:
# - file_downloads_total{status="success"} > 0
# - file_download_bytes_total > 0
# - admin_operations_total{operation="upload"} > 0
```

#### 8. Error Handling Test
```powershell
# Invalid blob ID
curl https://staging.example.com/secure/files/nonexistent/stream `
  -H "Authorization: Bearer $token"

# Expected: HTTP 404, {"detail": "Blob not found"}

# Invalid auth token
curl https://staging.example.com/secure/files/<blob_id>/stream `
  -H "Authorization: Bearer invalid_token"

# Expected: HTTP 401, {"detail": "Invalid token"}

# Missing auth header
curl https://staging.example.com/secure/files/<blob_id>/stream

# Expected: HTTP 401, {"detail": "Not authenticated"}
```

### Performance Benchmarks

Expected performance on staging (similar to prod specs):
- **Small files (<1MB):** <100ms download time
- **Medium files (1-10MB):** <1s download time
- **Large files (>100MB):** <5s download time (on gigabit connection)
- **Throughput:** >30 MB/s sustained
- **Memory:** <20MB per concurrent download
- **CPU:** <20% per concurrent download

Run load test:
```powershell
# Install hey (HTTP load testing tool)
go install github.com/rakyll/hey@latest

# Load test (10 concurrent, 100 requests)
hey -n 100 -c 10 `
  -H "Authorization: Bearer $token" `
  https://staging.example.com/secure/files/<blob_id>/stream

# Verify:
# - No 5xx errors
# - <5% error rate acceptable
# - Response time P95 < 2s
```

## Post-Deployment Verification

- [ ] All E2E tests passing
- [ ] Manual validation checklist complete
- [ ] Audit logs showing expected events
- [ ] Metrics dashboard showing activity
- [ ] No errors in application logs
- [ ] Performance benchmarks meet SLAs
- [ ] Monitoring alerts silent
- [ ] Staging status page green

## Rollback Procedure

If deployment fails or critical issues discovered:

### 1. Immediate Rollback (< 5 minutes)
```powershell
ssh user@staging << 'EOF'
# Stop current service
systemctl stop erp.service

# Restore previous version
cd /srv/erp
git checkout v1.2.0  # Previous release tag
source .venv/bin/activate
pip install -r requirements.txt

# Restart service
systemctl start erp.service
EOF

# Verify service health
curl https://staging.example.com/health
```

### 2. Database Rollback (if migrations run)
```powershell
ssh user@staging << 'EOF'
cd /srv/erp
source .venv/bin/activate
python -m alembic downgrade -1  # Rollback one migration
EOF
```

### 3. Restore from Backup (worst case)
```powershell
# Restore database from pre-deployment backup
# Restore file storage from backup
# Redeploy previous version as above
```

## Monitoring After Deployment

Monitor these metrics for 24 hours post-deployment:

### Application Metrics
- HTTP error rate (target: <1%)
- Response time P95 (target: <2s)
- Request rate (expect increase from new features)
- Memory usage (should remain stable)

### Business Metrics
- Blob uploads per hour
- Blob downloads per hour
- Storage utilization
- Active admin users

### Infrastructure Metrics
- CPU utilization (target: <70%)
- Memory utilization (target: <80%)
- Disk I/O (watch for spikes)
- Network throughput

### Alerts to Watch
- Service availability < 99.9%
- Error rate > 1%
- Response time > 5s (P95)
- Disk usage > 85%
- Memory usage > 90%

## Troubleshooting

### Issue: "Decryption failed" errors

**Symptoms:** Blobs fail to stream, "InvalidTag" in logs

**Resolution:**
1. Verify encryption key: `python -c "from hub.key_provider import get_key_bytes; print(len(get_key_bytes()))"`
2. Check if key changed during deployment
3. Restore correct key from secrets manager
4. Restart service

### Issue: Slow download speeds

**Symptoms:** Downloads taking much longer than expected

**Resolution:**
1. Check staging server CPU/memory: `htop`
2. Check disk I/O: `iostat -x 1 10`
3. Check network: `iperf3 -c <client>`
4. Increase chunk size in blob store configuration
5. Consider scaling up staging instance

### Issue: 401 Unauthorized errors

**Symptoms:** All authenticated requests failing

**Resolution:**
1. Verify JWT secret hasn't changed
2. Check token expiration
3. Verify admin role in token payload
4. Regenerate admin token if needed

## Notes

- This runbook assumes SSH-based staging; adapt to your deployment tooling (Kubernetes, Azure App Service, etc.)
- Do NOT use personal tokens for automated deploys — use a service principal or GitHub App
- Always test rollback procedure before deploying to production
- Keep this runbook updated with lessons learned from each deployment

## Success Criteria

Deployment is considered successful when:
- ✓ All automated tests passing
- ✓ Manual validation checklist complete (all items checked)
- ✓ No errors in logs for 1 hour post-deployment
- ✓ Performance benchmarks meet or exceed targets
- ✓ Monitoring dashboards show healthy metrics
- ✓ Stakeholders sign off on E2E validation

---

**Document Version:** 2.0  
**Last Updated:** 2025-11-28  
**Next Review:** Before production deployment
