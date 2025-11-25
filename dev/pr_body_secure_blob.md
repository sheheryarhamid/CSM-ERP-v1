# PR: feat/secure-blob-stream → main

This PR prepares the secure blob streaming feature for merge into `main`.

Summary
- Server: chunked AES-256-GCM streaming, Range support, admin RBAC, audit and metrics.
- Key provider: DPAPI + env fallback (operational runbook in `docs/secure-blob-stream.md`).
- Frontend: streaming consumer in `frontend/src/components/SecureFileViewer.jsx` with File System Access API fallback.
- Security: Replaced `python-jose` with `PyJWT`, added pip-audit CI workflow, removed runtime Redis/limiter.
- Changelog: `CHANGELOG.md` updated (Unreleased).

Checks performed locally
- `pytest`: 10 passed, 4 skipped
- `pylint` run and report saved to `dev/reports/pylint-report.txt`
- `pip-audit` run locally (no known vulnerabilities reported)

Post-merge steps (maintainer)
1. Verify CI (pip-audit, pylint, pytest) passes on remote.
2. Merge PR using squash/merge.
3. Run staging deploy and E2E validations (range/resume + streaming-to-disk).
4. Plan KMS integration for production key management and perform rolling key rotation.

Notes
- This branch intentionally removes runtime Redis dependency for the dev runtime; historical implementations are preserved in a backup branch.
- The PR creation script `dev/scripts/create_pr.ps1` can post the PR if `GITHUB_TOKEN` is set as an environment variable.
