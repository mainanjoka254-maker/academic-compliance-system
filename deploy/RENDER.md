# Deploying ADCS to Render

> **Limits I cannot bypass:** I cannot create Render services, provision an external database, or set your secrets from this environment. The repo is now Render-ready (pushed config + `render.yaml` blueprint). Complete the steps below in Render/dashboard.

## 0) Prerequisite: external MySQL 8
Render has **no managed MySQL**. ADCS requires MySQL (`mysql+pymysql`). Provision **MySQL 8** (e.g., DigitalOcean Managed MySQL, Aiven) in a private network/trusted-source setup. Create database/user and note `DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME`.

## 1) Create services from the blueprint
1. In Render: **New → Blueprint** and connect repo `mainanjoka254-maker/academic-compliance-system` (branch `main`).
2. Render reads `render.yaml` and proposes `adcs-backend` (Python web) and `adcs-frontend` (static).

## 2) Configure `adcs-backend` env vars (Render dashboard)
Required:
- `APP_ENV=production`, `DEBUG=False`, `SEED_DEMO_DATA=False`
- `SECRET_KEY` — strong unique 32+ chars (blueprint can generate; you may replace)
- `DB_HOST`, `DB_PORT` (3306), `DB_USER`, `DB_PASSWORD`, `DB_NAME` — external MySQL 8
- `FRONTEND_BASE_URL=https://<adcs-frontend>.onrender.com`
- `CORS_ORIGINS=https://<adcs-frontend>.onrender.com`

As needed:
- `SUPER_ADMIN_EMAIL`, `SUPER_ADMIN_PASSWORD`
- SMTP: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_TLS`
- Google OAuth: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI=https://<adcs-backend>.onrender.com/api/v1/auth/google/callback` (add the same redirect URI in Google Console; set JS origin to the frontend URL)

**Start/health (from blueprint):** runs `alembic upgrade head` then `uvicorn ... --port $PORT`; health check `/health`.

## 3) Configure `adcs-frontend` env var
- `VITE_API_BASE_URL=https://<adcs-backend>.onrender.com/api/v1`
The frontend uses this for cross-origin API calls (`ADCS/frontend/src/services/api.ts` falls back to `/api/v1`). SPA rewrite `/* → /index.html` is in the blueprint.

## 4) Deploy & verify
- Deploy backend first (migrations run on start), then frontend (rebuild picks up `VITE_API_BASE_URL`).
- Check `https://<adcs-backend>.onrender.com/health` → `{"status":"ok",...}` and open the frontend.
- Optional one-time seed (backend shell/job, from `ADCS/backend`): `python seed_kenya_institutions.py`.

## 5) Caveats
- **Not always-on on free tier:** Render free web services sleep (cold starts). Use a paid always-on instance for 24/7.
- **Uploads are ephemeral** unless you attach a persistent disk and set `DOCUMENT_STORAGE_PATH` accordingly; plan durable storage for `private_uploads` in production.
- **DB access/SSL:** ensure the external MySQL allows Render connectivity; configure SSL if your provider requires it.
- **Secrets:** never commit `.env`/credentials; rotate any previously exposed secrets.
