Central ERP Hub — Implementation Plan (Complete)

Version: 1.1 | Updated: November 19, 2025 | Owner: Sheheryar

This document is the delivery-ready implementation plan for the Central ERP Hub. It translates the high-level blueprint into concrete, testable requirements, developer workflows, operational runbooks, contracts, and acceptance criteria.

---

Executive Summary

- Goal: Deliver a secure, modular Central ERP Hub (infrastructure core) and three initial modules (Settings, KPI & Prescriptive Engine v1, POS skeleton) with a focus on Python backend and React frontend.
- Scale: Support Standalone (SQLite), LAN (MySQL), and Cloud (Postgres) with a migration path between these backends.
- Safety: Enforce module signing, sandboxing, least-privilege scopes, encrypted backups, and audited actions.

Scope (v1)

- Hub Core: Auth/RBAC, Env Manager, Unified Data API, Module Manager/Installer, Message Bus, Audit Logger, Backup Service.
- Modules: Settings (built-in), KPI & Prescriptive Engine (rule-based v1), POS (skeleton)
- Dev & Ops: OpenAPI, manifest schema & validator, module SDK, CI templates, DR runbook, tests

Acceptance Criteria

- Core API: OpenAPI generated and validated; auth enforced per endpoint.
- Module Manager: Validates manifests against schema and rejects unsigned/incompatible modules.
- Backup & DR: Daily backups with weekly restore tests documented and automated.
- Modules: Settings + KPI module installable via manifest, can send a recommendation to POS via message bus.
- Tests: Unit tests, module contract tests, integration smoke tests (SQLite/Postgres)

OpenAPI — Unified Data API (Endpoint Map)

Auth & Identity
- POST /auth/login -> returns tokens (access + refresh)
- POST /auth/logout -> revoke session
- POST /auth/refresh -> refresh access token

Modules & Manifests
- POST /modules/install -> upload manifest / URL
- GET  /modules -> list installed modules
- GET  /modules/{id} -> module details
- POST /modules/{id}/uninstall -> remove module (with rollback)

Sessions & Clients
- GET /api/health/clients -> summary + filters (store, role, module)
- GET /api/clients/{session_id} -> detail
- POST /api/clients/{session_id}/terminate -> revoke session

Data Resources (CRUD via Hub)
- GET /v1/{resource} -> list (pagination)
- POST /v1/{resource} -> create
- GET /v1/{resource}/{id} -> read
- PATCH /v1/{resource}/{id} -> update
- DELETE /v1/{resource}/{id} -> delete
- POST /v1/transaction -> transactional multi-entity operation (optional)

Admin & Ops
- GET  /admin/backup/status -> backup health
- POST /admin/backup/create -> trigger backup
- POST /admin/restore -> start restore job

Security: every route defines scopes; OpenAPI securitySchemes include Bearer JWT and optional mTLS client certs for service-to-service traffic.

Manifest Schema — Key Fields & Example

Required fields (manifest.yaml / manifest.json):
- name: String (human-friendly)
- id: String (stable module identifier, reverse DNS)
- version: SemVer
- api_version: Hub API contract version
- capabilities: Array[String]
- permissions: Array[String] (fine-grained scopes requested)
- db_requirements: Optional[Array] (tables, columns)
- dependencies: Optional[Array] (module ids)
- signed_by: Optional[String] (certificate fingerprint)
- upgrade_path: Optional[String] (notes)

Example:

```yaml
name: "KPI & Prescriptive Engine"
id: "com.example.kpi"
version: "1.0.0"
api_version: "v1"
capabilities:
  - analyzes_profit_trends
  - recommends_promotions
permissions:
  - read:products
  - read:sales
  - send:message_bus
db_requirements: []
dependencies: []
signed_by: ""
upgrade_path: "v1 -> v2: add forecast table; migration included"
```

Publish a JSON Schema at `docs/manifests/manifest-schema.json` used by CI and the Hub for validation.

Data Schema & Migration

- Canonical logical schema stored in `schemas/` (YAML + SQL). This is authoritative for all backends.
- Use Alembic for migrations. Every schema change must include: alembic script, backfill plan (if required), and a smoke test.
- Zero-downtime approach for major changes: shadow tables, dual writes, read adapters, backfill, and a safe cutover window.

Sync Protocol (Offline-First)

- Model: change-log + incremental deltas. For specific primitives use CRDTs (PN-Counters) for stock counts.
- Business transactions (orders/receipts): versioned items with conflict metadata; merged via deterministic rules or human review UI.
- Transport: HTTPS delta endpoints + WebSocket notifications; JWT for auth.
- Heartbeat: default 30s; device considered offline after 10m by default.

Message Bus & Messaging Contract

- Default: Redis Streams for MVP (simplicity, minimal infra). Provide adapters for RabbitMQ/NATS later.
- Envelope:
  - meta: {module, version, msg_id, timestamp, signature}
  - payload: JSON
  - idempotency_key: optional string
- Guarantee docs: define message types, schemas, and handling idempotency and retries.

Backup & DR Runbook (short)

- Policy: daily (14d), weekly (12w), monthly (12m); configurable.
- Backup contents: DB logical dumps, schema, module manifests, config snapshots, key metadata (no plaintext secrets).
- Encryption: AES-256 for archives; sign backups for integrity.
- Restore process (high level):
  1. Provision clean target environment
  2. Verify backup signature and integrity
  3. Restore config and manifests
  4. Restore DB (schema + data)
  5. Start Hub services, run smoke tests
- Weekly automated restore testing into staging; document results and retention.

Security & Compliance Checklist

- TLS enforced for all transports
- Secrets in KMS/HSM or OS-native stores (DPAPI only for Windows installs)
- Password hashing: Argon2 or bcrypt
- RBAC & least privilege
- Audit logs: append-only, tamper-evident; exportable for compliance
- Module signing and sandboxing
- SCA and dependency vulnerability scanning integrated into CI

Observability & Monitoring

- Metrics (Prometheus): latency, errors, active_sessions_total, queue_depth, backup_status
- Logs: structured JSON (fields: timestamp, request_id, user, module, action) with redaction rules
- Tracing (OpenTelemetry) optional for end-to-end traces
- Alerts: backup failure, high error rate, queue growth, session storms

Testing & CI/CD

- Tests per PR: unit tests, linters, contract tests (manifest + API mocks), integration smoke tests using docker-compose
- Release process: semver tagging -> CI builds images -> publish artifacts
- Provide a GitHub Actions template in `/ci/` for PR checks and release builds

Developer Experience

- Provide `module-sdk` (Python) including:
  - manifest generator
  - client helper for Unified Data API
  - message-bus helper for publishing/consuming
  - test harness (mock Hub)
- Provide `create-module` CLI to scaffold modules
- Provide `hub-local` docker-compose dev environment

Repo Layout (recommended)

- /hub/ — backend app, migrations, tests
- /modules/ — sample modules and scaffold
- /frontend/ — React app
- /docs/ — schemas, OpenAPI, manifests, runbooks
- /devops/ — docker-compose, k8s manifests
- /ci/ — CI workflows

Detailed Timeline (12 weeks)

- Week 0: Project setup, schemas, CI bootstrapping
- Weeks 1–2: Auth/RBAC, OpenAPI, basic UI shell
- Weeks 3–4: Alembic migrations, manifest validator, Settings module
- Weeks 5–6: Message bus, audit, backup service, weekly restore test
- Weeks 7–8: KPI rule-based engine, POS integration, contract tests
- Weeks 9–10: Observability, SLOs, security hardening
- Weeks 11–12: Integration testing (Postgres), perf tuning, release v0.1

Roles & Suggested Owners

- Product Owner: Sheheryar
- Tech Lead / Architect: (assign)
- Backend Lead: (assign)
- Frontend Lead: (assign)
- DevOps / SRE: (assign)
- QA / Test Lead: (assign)

Risks & Mitigations

- Migration risk: staging restores, backfills, feature-flagging
- Malicious modules: signing, sandboxing, review gates
- Offline sync complexity: iteratively implement (start simple), refine with CRDTs where necessary

Next Immediate Actions (choose one)

1) Produce `docs/manifests/manifest-schema.json` (manifest JSON Schema + example) — docs-only
2) Produce `api/openapi.yaml` (OpenAPI summary for the Unified Data API) — docs-only
3) Produce `docs/ops/backup-and-drrunbook.md` — step-by-step DR runbook and verification checklist
4) Create `module-sdk` skeleton (Python) and `create-module` CLI scaffold — code + tests

Tell me which action to take next; if you prefer, I can start with the manifest JSON Schema (1) and then generate the OpenAPI summary (2).
