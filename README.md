# Academic Compliance System (ADCS)

ADCS is a multi-institution academic compliance application built on the existing React/TypeScript frontend, FastAPI backend, SQLAlchemy, and MySQL. It includes email/password and optional Google OIDC authentication, role-protected dashboards, student and lecturer records, academic structure, document review, risk analysis, and institution-scoped compliance reporting.

## Technology and prerequisites

- Python 3.12 (the backend's tested environment)
- Node.js 20.19+ (Node 24 is used for the frontend tests and build)
- MySQL 8+
- Windows PowerShell examples below; use the corresponding shell syntax on other platforms

## Database setup

Create a database and a dedicated application account. Use a unique password in the SQL prompt and keep it private:

```sql
CREATE DATABASE adcs_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'adcs_user'@'127.0.0.1' IDENTIFIED BY '<unique-password>';
GRANT ALL PRIVILEGES ON adcs_db.* TO 'adcs_user'@'127.0.0.1';
FLUSH PRIVILEGES;
```

Copy `ADCS/backend/.env.example` to `ADCS/backend/.env` and set `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME`. The backend constructs a `mysql+pymysql` SQLAlchemy URL from these values. The actual `.env` is ignored by Git; do not paste it into chat or commit it.

From `ADCS/backend`, activate the project virtual environment and apply Alembic migrations:

```powershell
.\.venv\Scripts\Activate.ps1
alembic upgrade head
alembic current
alembic check
```

The verified migration head is `08aff36c2d00`. It includes Google identity, private academic documents, faculties, departments, academic programmes, course links, and lecturer programme assignments. Downgrades that would discard academic-structure records or assignments are refused.

### Accessing MySQL

Use MySQL Workbench with host `127.0.0.1`, port `3306`, database/schema `adcs_db`, and user `adcs_user`; enter the password stored in the private backend `.env` at the Workbench prompt.

Or use the MySQL CLI, which prompts for the password rather than putting it in shell history:

```powershell
mysql -h 127.0.0.1 -P 3306 -u adcs_user -p adcs_db
```

To confirm the connection from the backend without revealing credentials:

```powershell
Set-Location ADCS\backend
.\.venv\Scripts\python.exe -c "from sqlalchemy import text; from app.core.database import engine; c=engine.connect(); print(c.execute(text('SELECT 1')).scalar_one()); c.close()"
```

The application test suite overrides its database with SQLite for isolation; a passing test suite alone is not proof of MySQL connectivity. MySQL connectivity and Alembic migration checks are run separately.

## Installation and development

### Backend

```powershell
Set-Location ADCS\backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env locally; do not commit it.
alembic upgrade head
python seed.py
uvicorn app.main:app --reload --port 8000
```

API documentation: <http://localhost:8000/docs>

The seed script creates standard roles only and never inserts sample institutions. It does **not** create a default super-administrator. For a first installation only, set `SUPER_ADMIN_EMAIL` and `SUPER_ADMIN_PASSWORD` in the ignored `.env`; the password must be at least 16 characters and include lower/uppercase, a number, and a symbol. It must not include the email username. Run `python seed.py` once to bootstrap that platform administrator. A MySQL advisory lock serializes bootstrap attempts; bootstrap refuses to promote an ordinary account or create another platform administrator once one exists. After signing in, use **Institution management** in the Super Administrator dashboard to create a real institution, activate it, and create its institution administrator. Institution creation and administration APIs reject non-Super-Administrator users; public registration cannot create institutions. Registration options are read from active MySQL institution rows, and the registration endpoint rechecks that the selected institution remains active.

If an installation has no active institutions, students and lecturers cannot register yet. Bootstrap/sign in as the Super Administrator, create an institution, and ensure it is active; it will then appear in the registration selector. Lecturer registrations require a staff number, verified email, and approval from an authorized institutional administrator before the lecturer account is activated.

### Frontend

```powershell
Set-Location ADCS\frontend
npm ci
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` requests to `http://localhost:8000`.

## Authentication configuration

Email/password registration is student-only by design. Staff roles are assigned by authorized institutional administrators; Google sign-in never grants administrative roles. Email verification and password reset require SMTP delivery to be configured.

### Google OAuth / OpenID Connect (optional)

1. In Google Cloud Console, create/select a project and configure the OAuth consent screen.
2. Create an OAuth client ID with application type **Web application**.
3. Add `http://localhost:5173` under **Authorized JavaScript origins**.
4. Add `http://localhost:8000/api/v1/auth/google/callback` under **Authorized redirect URIs**.
5. Set these backend-only values in `ADCS/backend/.env`:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback`
6. Restart the backend. The login/register UI checks `/api/v1/auth/google/status` and leaves Google buttons disabled until server credentials are available.

Never put `GOOGLE_CLIENT_SECRET` in frontend code or a `VITE_` variable. The backend performs code exchange and ID-token validation, including issuer, audience, verified email, state, nonce, and PKCE. The implementation is covered by offline tests; external Google consent and callback testing still requires valid Cloud credentials and redirect registration.

### SMTP (optional for email verification and reset)

Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`, and `SMTP_TLS` in the backend `.env`. For Gmail, use an account with 2-Step Verification and an app password; do not use the account's normal password. Keep the SMTP secret server-side. Restart the backend and test verification/reset delivery with a controlled mailbox. SMTP delivery has not been live-tested until valid credentials are configured.

## Roles and modules

Backend routes enforce role permissions and institution scoping; frontend route guards are additional UX controls, not the security boundary. Current role identifiers are `super_admin`, `university_admin`, `registrar`, `compliance_officer`, `lecturer`, and `student`.

- Student registration/profile and academic records
- Lecturer account administration, profile/department assignment, faculty and programme setup, course teaching allocations, programme allocations, compliance status, and CSV reports
- Institution-scoped academic document uploads, review history, approval/rejection, and private downloads
- Deterministic compliance analysis of database-backed document uploads, incomplete/overdue assessments, upcoming deadlines, missing lecturer course submissions, and existing risk-engine factors
- Institution compliance summary and downloadable CSV at `/api/v1/compliance/analysis` and `/api/v1/compliance/analysis.csv`

Compliance analysis is deterministic and explainable, not a trained AI model. It does not change official results. “No student documents” means no upload is recorded; institutions have not configured required-document checklists. Lecturer report findings identify assigned courses without a report upload; lecturer submission deadlines are not currently configured. Assessment deadlines are detected only when a due date exists in the underlying academic record.

## Tests and verification

```powershell
Set-Location ADCS\backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\alembic.exe check

Set-Location ..\frontend
npm test
npm run build
npm audit
```

Backend tests cover authentication, role/institution isolation, documents, lecturers, academic structure, compliance analysis, and bootstrap credential validation. Frontend tests cover login/Google configuration, registration validation, role-based dashboards, lecturer teaching allocation, compliance reporting, and API error states. The test fixtures are isolated and do not act as production data.

## Dependency security status

The prior audit reported eight vulnerable dependency entries. They were remediated with compatible updates; no force upgrade was used. The production React Router 6-to-7 transition is exercised by dashboard tests and the build.

| Affected package | Dependency scope | Prior severity | Remediation |
|---|---|---:|---|
| `react-router` | Production, transitive | Moderate | `react-router-dom` 7.18.5 / `react-router` 7.18.5 |
| `react-router-dom` | Production, direct | Moderate | 7.18.5 |
| `vite` | Development, direct | High | 6.4.5 |
| `esbuild` | Development, transitive | Moderate | 0.25.12 |
| `vitest` | Development, direct | Critical | 4.1.12 |
| `tinypool` | Development, transitive | Critical | Removed from the resolved Vitest dependency tree |
| `@vitest/mocker` | Development, transitive | Moderate | 4.1.12 |
| `vite-node` | Development, transitive | Moderate | Removed from the resolved Vitest dependency tree |

The current full and production-only `npm audit` checks both report **zero vulnerabilities**.

## Production requirements and known limitations

- Configure production MySQL, a unique `SECRET_KEY` of at least 32 characters, `DEBUG=False`, TLS, trusted CORS origins, backups, SMTP, Google OAuth redirect URIs, and private upload storage before deployment. Settings validation rejects production mode with debug enabled or a placeholder JWT secret.
- Google authentication and real email delivery need external credentials for live end-to-end testing.
- Lecturer self-registration creates a pending, inactive request; institutional administrators or registrars must approve it after email verification. Super Administrators can create and manage institution administrators through the dashboard.
- The frontend test suite is automated; live browser workflows against production-grade credentials and a production dataset remain deployment checks.
- Faculty/programme records were added by migration `08aff36c2d00`; apply `alembic upgrade head` before deploying this version.
- Department/course management beyond the lecturer-administration workflows is still limited; do not treat unimplemented flows as complete.

See [PROJECT_PROGRESS.md](./PROJECT_PROGRESS.md) for the latest verification and implementation status.
