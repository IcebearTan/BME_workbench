# BME Workbench development rules

Read `README.md`, `docs/ARCHITECTURE.md` and `docs/IDENTITY-CONTRACT.md` before changing this repository. This is an independent project; adjacent BME repositories are references, not runtime dependencies.

- Keep Vue 3, Vite, Vue Router, Vuex, Element Plus and the vendored DewUI design foundation. Use Flask, SQLAlchemy and explicit database migrations for the backend.
- Separate external authentication, central club admission, local workspace membership and local governance permissions. Do not infer local permissions from central roles or from email.
- No local passwords or points-store login dependency. Training-platform integration is not live until its provider endpoints are implemented and verified. Missing or unavailable identity configuration must not grant access.
- Preserve browser-bound login state, one-time callback consumption, HttpOnly independent sessions, CSRF validation and server-side permission checks. Do not put session credentials in localStorage.
- Account identity is `(issuer, subject)`. Person restrictions use stable `(issuer, person_id)`. Never merge accounts by matching display names or email addresses.
- Real secrets, private keys, `.env` files, databases, user uploads and production data must not be committed. Examples contain no usable production credentials.
- Use icons from `@element-plus/icons-vue` or SVG, no emoji in new UI, logs, source or comments. Do not introduce external font/script CDNs.
- Local ports: frontend 8083, backend 5003, browser tests 18083. Do not change training-platform development settings or connect tests to production.
- Keep packages self-contained. Record the source commit for imported UI code in `packages/PROVENANCE.md`; never reference an adjacent repository with a runtime relative path.
- Before a commit, run `pnpm check:no-emoji`, `pnpm build`, `pnpm test:e2e`, and the backend isolated test suite. Add targeted security regression cases for changes to authentication and authorization.
- Do not automatically migrate production databases, seed live users, deploy, or push. The GitHub remote will be supplied by the owner separately.

The initial scope is an identity foundation and application shell. Existing work tasks, files, cross-group deliveries and historical data remain in the original platform until separately migrated under `docs/MIGRATION.md`.
