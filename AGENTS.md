# BME Workbench development rules

Read `README.md`, `docs/ARCHITECTURE.md` and `docs/IDENTITY-CONTRACT.md` before changing this repository. This is an independent project; adjacent BME repositories are references, not runtime dependencies.

- Keep Vue 3, Vite, Vue Router, Vuex, Element Plus and the vendored DewUI design foundation. Use Flask, SQLAlchemy and explicit database migrations for the backend.
- Separate external authentication, central club admission, local workspace membership and local governance permissions. Do not infer local permissions from central roles or from email.
- No local passwords or points-store login dependency. Training integration uses dedicated /workbench-sso endpoints, fixed callbacks and PKCE. Missing or unavailable identity configuration must not grant access.
- Preserve browser-bound login state, one-time callback consumption, HttpOnly independent sessions, CSRF validation and server-side permission checks. Do not put session credentials in localStorage.
- Account identity is `(issuer, subject)`. Person restrictions use stable `(issuer, person_id)`. Never merge accounts by matching display names or email addresses.
- Real secrets, private keys, `.env` files, databases, user uploads and production data must not be committed. Examples contain no usable production credentials.
- Use icons from `@element-plus/icons-vue` or SVG, no emoji in new UI, logs, source or comments. Do not introduce external font/script CDNs.
- Local ports: frontend 8083, backend 5003, browser tests 18083. Do not change training-platform development settings or connect tests to production.
- Keep packages self-contained. Record the source commit for imported UI code in `packages/PROVENANCE.md`; never reference an adjacent repository with a runtime relative path.
- Before a commit, run `pnpm check:no-emoji`, `pnpm build`, `pnpm test:e2e`, and the backend isolated test suite. Add targeted security regression cases for changes to authentication and authorization.
- Do not automatically migrate production databases, seed live users, deploy, or push. The GitHub remote will be supplied by the owner separately.

The collaboration domain has been ported under backend/workbench/collab. The club_* tables are read-only source projections; internal_group_member is workbench-owned organization truth, supports multiple groups and coordinators, and must preserve membership periods. Application admission remains centrally verified through the dedicated workbench service client. Follow docs/DEPLOYMENT-2026-10-13.md for actual migration and retirement state; never re-enable old writes after cutover without reconciliation. The user authorized IP-only campus HTTP deployment; keep that exception explicit and limited to private IPs, with client-secret backchannels restricted to loopback.
