# Central ERP Hub - Quick Start Guide

## Development Environment Setup

### Prerequisites
- Python 3.11+
- Git
- Windows (DPAPI support) or Linux/Mac (env-based keys)

### 1. Install Dependencies

```powershell
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.\.venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source .venv/bin/activate

# Install required packages
pip install -r requirements.txt

# Optional: Install performance monitoring
pip install psutil

# Optional: Install cloud KMS providers (as needed)
pip install boto3  # AWS KMS
pip install azure-keyvault-secrets azure-identity  # Azure Key Vault
pip install google-cloud-kms  # GCP KMS
```

### 2. Configure Environment

Create `.env` file in project root:

```bash
# Development - Generate a random 32-byte key
BLOB_KEY=your_64_character_hex_key_here

# Optional: Admin authentication
ADMIN_TOKEN=your_secret_admin_token
ADMIN_JWT_SECRET=your_jwt_secret_key

# Optional: Redis (for distributed sessions)
# REDIS_URL=redis://localhost:6379

# Optional: Logging
LOG_LEVEL=INFO
```

Generate BLOB_KEY (PowerShell):
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Generate BLOB_KEY (Linux/Mac):
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Run the Application

```powershell
# Set environment and start server
$env:PYTHONPATH = '.'
$env:BLOB_KEY = 'your_generated_key_here'

# Start FastAPI server
uvicorn hub.main:app --host 127.0.0.1 --port 8000 --reload
```

Alternative using Python directly:
```powershell
python -c "import os; os.environ['BLOB_KEY']='your_key'; os.environ['PYTHONPATH']='.'; import uvicorn; uvicorn.run('hub.main:app', host='127.0.0.1', port=8000, reload=True)"
```

### 4. Access the Dashboard

Open your browser:
- **Main Dashboard**: http://127.0.0.1:8000/ (redirect to dashboard)
- **Dashboard UI**: http://127.0.0.1:8080/index.html (if static server running)
- **API Documentation**: http://127.0.0.1:8000/docs
- **Health Check**: http://127.0.0.1:8000/health
- **Metrics**: http://127.0.0.1:8000/metrics

### 5. Run Tests

```powershell
# Smoke tests
$env:PYTHONPATH = '.'
python dev\scripts\smoke_test.py

# Performance tests (quick - 10MB)
$env:PYTHONPATH = '.'
$env:BLOB_KEY = 'your_key'
python -c "import os,sys; sys.path.insert(0,'.'); from dev.scripts.streaming_perf import test_chunking_variations; test_chunking_variations()"

# Full performance suite (100MB+)
python dev\scripts\streaming_perf.py
```

### 6. Serve Frontend

```powershell
# Start static file server for frontend
python -m http.server 8080 --directory dev/frontend

# Then open: http://127.0.0.1:8080/index.html
```

---

## Production Deployment

For production deployment, follow the comprehensive guides:

1. **Pre-Deployment Checklist**: `docs/PRE_DEPLOYMENT_CHECKLIST.md`
2. **Staging Deployment**: `dev/runbooks/staging_deploy.md`
3. **Production Rollout**: `docs/production-rollout.md`
4. **Architecture Alignment**: `docs/BLOB_STREAMING_ARCHITECTURE_ALIGNMENT.md`

### Production Environment Variables

```bash
# KMS Configuration (choose one provider)

# AWS KMS
AWS_KMS_KEY_ID=alias/erp-hub-blob-encryption
AWS_REGION=us-east-1
# AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY (or use IAM role)

# Azure Key Vault
AZURE_KEY_VAULT_URL=https://mykeyvault.vault.azure.net/
AZURE_KEY_NAME=erp-blob-encryption-key
# Use managed identity or set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID

# GCP KMS
GCP_PROJECT_ID=my-project
GCP_KEYRING=erp-hub-keyring
GCP_KEY_NAME=blob-encryption-key
GCP_LOCATION=global
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Application
ENABLE_BLOB_STREAMING=true
LOG_LEVEL=INFO

# Optional: Redis for distributed sessions
REDIS_URL=redis://production-redis:6379

# Security
ADMIN_JWT_SECRET=your_production_jwt_secret
# Do NOT use ADMIN_TOKEN in production
```

### Production Startup

```bash
# With KMS (recommended)
uvicorn hub.main:app --host 0.0.0.0 --port 8000 --workers 4

# With Docker
docker run -d \
  --name erp-hub \
  -p 8000:8000 \
  -e AWS_KMS_KEY_ID=alias/erp-hub-blob-encryption \
  -e AWS_REGION=us-east-1 \
  erp-hub:latest

# With systemd
sudo systemctl start erp-hub
sudo systemctl enable erp-hub
```

---

## Quick Reference Commands

### Health & Status
```powershell
# Check server health
Invoke-RestMethod http://127.0.0.1:8000/health

# View metrics
Invoke-RestMethod http://127.0.0.1:8000/metrics

# List active sessions
Invoke-RestMethod http://127.0.0.1:8000/api/health/clients
```

### Create Session
```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/clients/create?user=demo&role=Manager" -Method POST
```

### Test KMS Provider
```powershell
$env:PYTHONPATH = '.'
python hub\kms_provider.py
```

---

## Troubleshooting

### Port Already in Use
```powershell
# Find process using port 8000
netstat -ano | findstr ":8000"

# Kill process (replace PID)
taskkill /PID <PID> /F
```

### BLOB_KEY Not Configured
```powershell
# Generate and set key
$key = python -c "import secrets; print(secrets.token_hex(32))"
$env:BLOB_KEY = $key
```

### Module Import Errors
```powershell
# Ensure PYTHONPATH is set
$env:PYTHONPATH = '.'

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### KMS Provider Errors
- Ensure cloud CLI is configured (`aws configure`, `az login`, `gcloud auth`)
- Verify IAM permissions for KMS key access
- Check environment variables are set correctly

---

## Architecture Overview

```
Central ERP Hub
├── hub/                    # Core backend
│   ├── main.py            # FastAPI application
│   ├── blob_store.py      # Encrypted blob storage
│   ├── key_provider.py    # DPAPI/env key management
│   ├── kms_provider.py    # Cloud KMS integration
│   ├── auth.py            # Authentication utilities
│   ├── audit.py           # Audit logging
│   └── session_store.py   # Session management
├── dev/
│   ├── frontend/          # Web UI
│   │   ├── index.html     # Main dashboard
│   │   └── secure-file-viewer.html  # Blob viewer
│   ├── scripts/           # Testing & utilities
│   └── runbooks/          # Deployment procedures
├── docs/                  # Documentation
├── requirements.txt       # Python dependencies
└── .env                   # Environment config (create this)
```

---

## Support & Documentation

- **Master Blueprint**: `🏢 Central ERP Hub – The Official Master.ini`
- **Release Notes**: `dev/RELEASE_NOTES_v1.3.0.md`
- **Architecture Alignment**: `docs/BLOB_STREAMING_ARCHITECTURE_ALIGNMENT.md`
- **API Documentation**: http://127.0.0.1:8000/docs (when running)

---

## Next Steps

1. ✅ Complete development setup (this guide)
2. ⏳ Deploy to staging (`dev/runbooks/staging_deploy.md`)
3. ⏳ Production rollout with KMS (`docs/production-rollout.md`)
4. ⏳ Final sign-off and monitoring setup

**Current Progress**: 95% complete - Ready for deployment!
