# Staging Deploy Runbook

This runbook documents the steps required to deploy the current `main` branch to staging and run E2E validations for secure blob streaming.

Prerequisites
- A staging environment with credentials (service principal, SSH key, or GitHub App installation token).
- Access to staging database and object store (if applicable).
- `STAGING_DEPLOY_KEY` or service principal stored in your secret manager.

Steps
1. Prepare build
   - From repo root:
     ```powershell
     git checkout main
     git pull origin main
     py -3 -m pip install -r requirements.txt
     cd frontend
     npm ci
     npm run build
     cd ..
     ```
2. Deploy backend (example using SSH + systemd)
   - Copy artifacts or push container image to registry.
   - On staging host:
     ```powershell
     scp -r ./hub user@staging:/srv/erp
     ssh user@staging 'cd /srv/erp && .venv/Scripts/Activate.ps1; pip install -r requirements.txt; systemctl restart erp.service'
     ```
3. Deploy frontend
   - Upload `frontend/dist` to your static hosting or restart frontend service.
4. Run migrations (if any)
   - `py -3 -m alembic upgrade head` (run on staging DB)
5. Run E2E tests (range / resume / streaming-to-disk)
   - From repo root, run automated tests that exercise secure-file endpoints and client streaming consumer. Example:
     ```powershell
     py -3 -m pytest tests/test_secure_streaming.py -q
     ```
6. Manual checks
   - Visit the Secure File Viewer UI and download a >100MB test blob using the streaming option. Verify progress, cancel/resume, and that the UI never shows filesystem paths.
   - Check audit logs for read events and ensure Prometheus metrics increased accordingly.

Rollback
- If a deploy fails, rollback to previous container/image tag or restore files from backup and restart services.

Notes
- This runbook assumes SSH-based staging; adapt to your deployment tooling (Kubernetes, Azure App Service, etc.).
- Do NOT use personal tokens for automated deploys — use a service principal or GitHub App.

Blockers
- I cannot execute the staging deploy from here without staging credentials and network access. Provide credentials or follow the steps above locally or via your CI.
