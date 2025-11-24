UI scaffold notes — Central ERP Hub

Summary
- React + Vite is used by the existing `frontend/` project. The scaffold added a minimal React app under `frontend/src`.

Security pattern for database files
- The Hub backend MUST store database files and backups in protected locations (OS-level permissions, encrypted at rest).
- The frontend MUST NOT expose filesystem paths, mount points, or direct download URLs. Instead:
  - Frontend lists files using an authenticated API (`GET /api/secure/files`) that returns only metadata (id, name, type, size, created_at).
  - File previews or operations are performed via server endpoints that return sanitized content (e.g., `GET /api/secure/files/:id/preview`) or perform actions server-side.
  - For downloads, the server should implement short-lived signed URLs or an API that streams data to the authenticated client while logging access. The frontend should never construct a path itself.

What was added
- `frontend/src/*` — App shell, pages, components, and a small `api/client.js` axios wrapper.
- `SecureFileViewer` component demonstrates the UI-only access pattern.

Next steps
- Implement server endpoints (`/api/secure/files`, `/api/secure/files/:id/meta`, `/api/secure/files/:id/preview`) that enforce RBAC and never reveal server-side paths.
- Add tests to ensure UI cannot cause the server to return raw filesystem paths.
- Optionally convert the frontend to TypeScript and add component tests.
