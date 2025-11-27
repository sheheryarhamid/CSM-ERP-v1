# Release Notes - v1.3.0

## 🔐 Secure Blob Streaming Release

**Release Date:** 2025-11-28  
**Type:** Major Feature Release  
**Status:** Production Ready

### Overview

This release introduces enterprise-grade secure blob streaming with server-side AES-256-GCM encryption, HTTP Range support for resumable downloads, and comprehensive audit logging.

## 🎯 Key Features

### 1. Chunked Encrypted Blob Storage
- Server-side encryption using AES-256-GCM
- Streaming-friendly format with per-chunk authentication
- Memory-bounded operations for files of any size

### 2. HTTP Range Request Support (RFC 7233)
- Partial content delivery with `206 Partial Content`
- Resumable downloads for large files
- Efficient seeking without full decryption

### 3. Flexible Key Provider Architecture
- Pluggable key management
- DPAPI support (Windows)
- Environment variable fallback
- KMS-ready for production deployments

### 4. Admin RBAC & Audit Logging
- Role-based access control
- JWT authentication
- Comprehensive audit trail
- Prometheus metrics

## 🔄 Breaking Changes

1. **Session Store API Refactored** - Now uses `SessionSpec` objects
2. **Redis No Longer Required** - In-memory store is default
3. **Authentication Hardening** - All `/secure/*` endpoints require admin JWT

## 📊 Performance

- 100MB file streaming: ~2.15s (46.51 MB/s)
- Memory usage: <15MB for any file size
- Benchmark suite: `dev/scripts/streaming_perf.py`

## 🛡️ Security

- AES-256-GCM encryption (FIPS 140-2 approved)
- Removed vulnerable `ecdsa` dependency
- Automated dependency scanning in CI

## 📚 Documentation

- `docs/secure-blob-stream.md` - Operational guide
- `dev/scripts/streaming_perf.py` - Performance tests
- `dev/frontend/secure-file-viewer.html` - Demo application

## 🚀 Deployment

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure key
export BLOB_KEY=$(python -c "import os; print(os.urandom(32).hex())")

# 3. Start
uvicorn hub.main:app --host 0.0.0.0 --port 8000
```

See `dev/runbooks/staging_deploy.md` for production procedures.

---

*Full release notes: [CHANGELOG_v1.3.0.md](./dev/CHANGELOG_v1.3.0.md)*
