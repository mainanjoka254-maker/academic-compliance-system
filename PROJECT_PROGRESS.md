# ADCS Project Progress

## Latest completed milestones

- **Backend authorization review and seed hardening:** A read-only review found one high-confidence issue: the seed script supplied a public default super-admin email/password. Removed both defaults, made super-admin creation opt-in, require a strong explicit password, and prevent promotion of an existing non-superuser account. Production settings now reject debug mode and placeholder/short JWT secrets. Added tests for bootstrap and production security validation. The review found no other high-confidence API authorization or tenant-isolation issues.
- **Lecturer administration:** Added lecturer onboarding, profile editing/deactivation, department assignment, course teaching allocations, programme allocations, compliance status, and CSV reporting. New faculty, department, and academic-programme APIs are institution-scoped, validate parent records, and audit lecturer/programme assignments. Admin and registrar dashboards expose the management UI.
- **Academic structure migration:** Added faculties, faculty-linked departments, academic programmes, course/programme links, and lecturer/programme assignments in revision `08aff36c2d00`. That migration remains applied; the current head is `66a9043e5b42`. MySQL upgrade, guarded downgrade, re-upgrade, and `alembic check` passed for the academic structure; the downgrade refuses to drop its rows or assignments.
- **Compliance analysis:** Added deterministic institution-level analysis using live database records for students without document uploads, incomplete/overdue assessments, upcoming assessment deadlines, assigned courses without lecturer reports, and existing student risk factors. Added scoped JSON and CSV endpoints and an admin/registrar/compliance dashboard panel. The report states its rules-based nature and its limitations; it does not alter results or claim model training.
- **Frontend automated tests:** Added Vitest 4 with jsdom and React Testing Library. Tests cover login and Google configuration UI, registration validation, role-based dashboards, lecturer teaching allocations, compliance summaries, and API error states.
- **Dependency security:** Updated React Router to 7.18.5, Vite to 6.4.5, Vitest to 4.1.12, and compatible transitive dependencies. No force upgrade was used. Full and production-only npm audits both report **0 vulnerabilities**.
- **Security documentation:** Removed the outdated README default-super-admin credentials. Added Google/SMTP setup, development and test instructions, MySQL access instructions, production requirements, and dependency remediation details in [README.md](./README.md).
- **Institution seed-data safeguard:** Removed the opt-in hardcoded institution list from the seed command. Seeding now creates system roles only (and the explicitly configured one-time super-admin); real institutions are created through the authenticated Super Administrator API. Existing MySQL records were not deleted or changed.
- **Institution onboarding:** Added Super Administrator-only institution create/edit/activate/deactivate and institution-administrator create/list/activate/deactivate APIs and dashboard UI. Added one-time explicit environment-based Super Administrator bootstrap protection; the seed command cannot promote an ordinary account or create another platform administrator once one exists. No institution or user was hardcoded or inserted by this work.
- **Registration flow:** Student registration continues to validate an active institution and persists institution IDs in MySQL. Lecturer registration now accepts a staff number, verifies email, and remains inactive without a lecturer role until an authorized institution administrator approves it. Institutional admins and registrars can view and approve/reject institution-scoped requests. Privileged roles remain unavailable through public registration.
- **Database migration:** Added migration `66a9043e5b42` for lecturer request/approval state. Applied to MySQL; Alembic reports this as head with no schema drift.
- **Live institution check:** MySQL is reachable. The initial check during investigation found no institutions/admin; the latest live query found 16 active institutions and one Super Administrator, and the public registration-options API returned those 16 records (HTTP 200). Existing MySQL records were left untouched.
- **Browser smoke test:** Refreshed the registration page and confirmed all 16 live MySQL institution names appear. Switched account type to Lecturer and verified the staff-number field and approval wording appear; Google registration is disabled for that role. No new institution or lecturer was inserted into the real database for testing; workflow tests use the isolated test database.

## Verification results

- Backend: **38 passed** using the isolated test database.
- Frontend: **14 passed** across 4 test files; TypeScript check and production build passed.
- Frontend TypeScript check and production build: **passed** with Vite 6.4.5.
- MySQL: direct `SELECT 1` connection check **passed** without exposing environment values.
- MySQL institution options: 16 active rows were returned by the live public API; no test rows were added.
- Alembic: current head `66a9043e5b42`; migration applied; `alembic check` reports **no schema drift**.
- Bootstrap: MySQL advisory-lock acquire/release verified; first-admin seeding is serialized on a dedicated MySQL connection.
- Migration procedure: academic-structure migration downgrade and re-upgrade **passed** after correcting MySQL foreign-key index drop ordering; rollback is guarded against data loss.
- `py_compile` passed for changed Python modules.
- No files have been staged or committed.

## Implemented modules

- MySQL/SQLAlchemy connection through the ignored backend `.env` and Alembic-managed migrations.
- Email registration, login, verification/reset flows, Google OIDC authorization-code flow, state/nonce/PKCE, verified-email linking, and role-aware routing.
- Backend role checks and institution scoping, including student/lecturer/case/risk/document paths covered by regression tests.
- Student and lecturer profiles, courses, assessments, attendance, documents, verification history, audit records, notifications, and dashboards.
- Faculty/department/programme entities and lecturer teaching/programme assignments.
- Deterministic compliance and risk reporting from persisted records, including CSV downloads.

## Remaining production work and limitations

- **Google OAuth and SMTP:** No live external credentials are configured. Google consent/callback and actual SMTP delivery still require the user's Google Cloud and mail-provider configuration and live testing.
- **Required-document policy:** There is no institution-configured checklist of required document types; the current analysis reports when no upload is recorded and says so explicitly.
- **Lecturer submission deadlines:** The current data model does not configure lecturer report deadlines; course-without-report findings are not called overdue.
- **Bootstrap:** Use the existing authorized Super Administrator account where available. First installations must configure explicit strong bootstrap credentials in the ignored backend `.env` and run `python seed.py` once. The latest verified state is 16 active institutions and one Super Administrator.
- **Operational deployment:** Configure production secrets, HTTPS, CORS allowlist, MySQL backups, SMTP, Google callback origins, private file storage, and Windows/MySQL service lifecycle before production use.
- **Backend warning cleanup:** Test runs still emit deprecation warnings from existing FastAPI lifecycle, UTC datetime, and dependency APIs; these are not test failures and were not changed as unrelated work.
- Some broader dashboard workflows and administrator-facing data management beyond lecturer/academic-structure screens remain limited; see the known limitations in [README.md](./README.md).

## Runtime configuration

- Backend environment: `ADCS/backend/.venv`, Python 3.12.10.
- Frontend runtime used for verification: Node 24.19.0.
- Database: MySQL schema `adcs_db`; host/user/password values remain in the private ignored backend `.env`.
- Google values: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`.
- SMTP values: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, sender fields, and TLS setting.

## Inspection report (current takeover)

- Architecture: React/Vite frontend, FastAPI backend, SQLAlchemy, MySQL (adcs_db), Alembic migrations.
- Completed modules: auth (email+Google), roles/institution scoping, students/lecturers, academic structure, documents, compliance analysis, notifications, audit.
- Incomplete: required-document policy, lecturer report deadlines, initial admin/institution bootstrap UX, deployment hardening, deprecation warnings.
- DB/migration: head 08aff36c2d00, alembic check passed, MySQL connectivity passed.
- Auth: email verification/reset and Google OIDC implemented; external credentials not configured.
- Security: production validation for DEBUG/SECRET_KEY; no default super-admin; institution scoping tested.
- Errors: none failing; 38 backend tests, 13 frontend tests, build passed; deprecation warnings remain.
- Next priorities: required-document policy, lecturer deadlines, bootstrap guidance, warning cleanup.

Use MySQL Workbench with host `127.0.0.1`, port `3306`, schema `adcs_db`, and the account configured in the ignored backend `.env`. Alternatively run `mysql -h 127.0.0.1 -P 3306 -u adcs_user -p adcs_db`; `-p` prompts for the password without placing it in shell history. Full setup details are in [README.md](./README.md).

## Latest changes
- Network access enabled (0.0.0.0) for phone use; phone URL http://172.20.122.74:5173.
- Added profiles, settings, announcements, support tickets, stats endpoints and migrations.
- Frontend Settings page and animated background added.


## 2026-11-09 (Kilo) - Kenya institutions seed
- Added idempotent seed script ADCS/backend/seed_kenya_institutions.py (safe insert-only; matches by code/name; no deletes/overwrites).
- Seeded Kenyan higher-education & TVET institutions into primary DB: **120 total** (71 universities, 3 university colleges, 11 national polytechnics, 35 TVET institutes/colleges), all active, country=Kenya.
- Registration options and homepage stats now reflect real DB data. Backend tests: 42 passed; alembic check clean.


## 2026-11-09 (Kilo) - Production deployment package (Docker) + LAN phone access
- Added production-ready Docker stack: docker-compose.prod.yml, deploy/backend.Dockerfile (alembic upgrade head + uvicorn, restart always, /health), deploy/frontend.Dockerfile + deploy/nginx.conf (SPA + /api proxy), deploy/.env.production.example, deploy/DEPLOYMENT.md, .dockerignore.
- Frontend serves/proxies API (no localhost on clients); DB private in compose; MySQL 8 image for strict MySQL (managed MySQL recommended). Honest note: free tiers may sleep - 24/7 needs an always-on host (e.g., DO Droplet/VPS).
- LAN verified: http://172.31.27.155:4173 (app) and backend health OK on LAN IP; CORS/preview proxy configured.
- Tests after packaging: backend 42 passed, frontend 14 passed, build OK. No secrets committed.


## 2026-11-09 (Kilo) - Windows local always-on scripts
- Added deploy/windows/install-adcs-autostart.ps1, start-adcs-now.ps1, uninstall-adcs-autostart.ps1 (Scheduled Tasks for MySQL/Backend/Frontend, restart-on-failure). **Requires Admin PowerShell** to register ONLOGON tasks (creation was access-denied in this session).
- Updated deploy/DEPLOYMENT.md with Windows auto-start steps. Services currently running and verified (health 200, frontend 4173).
- Honest: keeps ADCS active while laptop is on; not 24/7 independent of laptop. No secrets committed.

