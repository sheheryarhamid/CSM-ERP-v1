PR: chore/lint-cleanup/part-1 -> pr/lint-cleanup-ready

Summary:
- Implement server-side encrypted blob streaming (chunked AES-GCM) with Range/resume support.
- Add DPAPI key provider + env fallback for blob key retrieval.
- Remove runtime Redis requirement by using in-memory session store (Redis left opt-in).
- Add admin RBAC helpers, audit logging, and Prometheus metrics for file downloads and admin ops.
- Refactor session-store API to accept a single spec object; deduplicate in-memory implementation.
- Frontend: added a streaming consumer demo and a smoke-test script (dev/scripts/smoke_test.py).
- Linting/format: ran `isort` and `black --line-length 100`, fixed many pylint issues (docstrings, narrower excepts, extracted helpers).

Artifacts and reports:
- pytest report: `dev/reports/pytest-after-docs3.txt`
- pylint report: `dev/reports/pylint-after-docs3.txt`
- intermediate reports: `dev/reports/` (many incremental runs captured)

Notes & deployment:
- App runs locally via `uvicorn hub.main:app --host 127.0.0.1 --port 8000`.
- Interactive Swagger UI: http://127.0.0.1:8000/docs
- Required env vars for production usage of blob encryption:
  - `BLOB_KEY` (hex, 16/24/32 bytes) OR `KEY_PROVIDER=dpapi` + `BLOB_KEY_DPAPI`/`BLOB_KEY_DPAPI_FILE` on Windows.
- `requirements.txt` created from the current venv.

Next steps (suggested):
1. Address remaining small pylint warnings (Windows interop naming in `hub/key_provider.py`).
2. Add CI step to run `black`, `isort`, `pylint`, `pytest` and `pip-audit`.
3. Add production KMS/HSM key provider and rotate strategy for `BLOB_KEY`.

Reviewer checklist:
- Verify `dev/reports/pytest-after-docs3.txt` for test coverage.
- Run the app locally and inspect `/docs` and `/secure/files` endpoints.
- Review `hub/blob_store.py` streaming format for AES-GCM compatibility.
