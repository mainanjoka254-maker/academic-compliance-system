# ADCS Deployment & Operations (DigitalOcean / always-on)

> Honest note on “free + always on”: a truly 24/7 public deployment (independent of your laptop) needs an always-on host and a reliable database. Many free tiers sleep or have limits. The stack below is **production-ready** and works on any always-on Docker host (DigitalOcean Droplet/VPS). If you use a “free” host, **verify its uptime/eligibility/terms** — I cannot guarantee 24/7 on a free tier.

## What this provides
- **Frontend**: Nginx serves the built React SPA and proxies `/api` to the backend (no `localhost` on phones/clients).
- **Backend**: FastAPI (Uvicorn) behind proxy headers, **`alembic upgrade head` on start** (idempotent), `restart: always`, `/health` check.
- **Database**: MySQL 8 in Compose (strict MySQL). **Recommended for production:** DigitalOcean Managed MySQL (private), not publicly exposed.
- **Persistence**: Docker volumes for MySQL data and `private_uploads`.
- **Security defaults**: DB not published; secrets via env file (never commit). Set `DEBUG=False`, strong `SECRET_KEY` (32+), strict `CORS_ORIGINS`/`FRONTEND_BASE_URL`.

## DigitalOcean (VPS) quick start
1. Create a Droplet (Ubuntu 22.04/24.04, 2GB+ recommended). Add your SSH key. (Paid resource — confirm current pricing.)
2. Point firewall: allow **22** (SSH, restricted to your IP), **80** (HTTP), **443** (HTTPS when you add a domain). Do **not** expose 3306.
3. Install Docker + Compose plugin; clone/upload this repo.
4. `cp deploy/.env.production.example deploy/.env.production` and fill **strong unique** secrets, `FRONTEND_BASE_URL`/`CORS_ORIGINS` = `http://<DROPLET_IP>` (no domain yet).
5. `docker compose --env-file deploy/.env.production -f docker-compose.prod.yml up -d --build`
6. Verify: `curl http://<DROPLET_IP>/health` and open `http://<DROPLET_IP>`.
7. (Optional, one-time) seed Kenya institutions inside backend container:
   `docker compose --env-file deploy/.env.production -f docker-compose.prod.yml exec backend python seed_kenya_institutions.py`

## HTTPS + domain (when you get one)
- Set DNS A record to the droplet IP; update `FRONTEND_BASE_URL`/`CORS_ORIGINS` to `https://yourdomain`.
- Add TLS termination (recommended: **Caddy** as a reverse proxy for automatic Let’s Encrypt, or Nginx+certbot, or DO Load Balancer). Keep the app containers private behind it.

## Managed MySQL (recommended)
- Create a DO Managed MySQL database (private network/VPC). Set `DB_HOST/PORT/USER/PASSWORD/NAME` in `deploy/.env.production`.
- Remove or disable the `db` service in Compose and point `backend` to managed MySQL. Keep DB credentials private; restrict trusted sources.

## Backups & restore
- **MySQL volume backup:** `docker run --rm -v adcs_mysql_data:/var/lib/mysql -v $(pwd):/backup alpine tar czf /backup/mysql-data.tar.gz -C /var/lib/mysql .`
- **Logical backup (preferred):** `docker compose --env-file deploy/.env.production -f docker-compose.prod.yml exec db sh -lc 'mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --all-databases' > backup.sql`
- **Restore logical:** `cat backup.sql | docker compose ... exec -T db sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD"'`
- **Uploads:** back up the `adcs_uploads` volume (`private_uploads`). Test restores.
- Automate backups (cron) and store copies off the droplet.

## Operations
- Status: `docker compose --env-file deploy/.env.production -f docker-compose.prod.yml ps`
- Logs: `... logs -f backend` / `frontend` / `db`
- Update: pull code, `... up -d --build` (migrations run on backend start).
- Health: `/health` (proxied). Configure external uptime monitoring/alerts.

## Windows: keep ADCS active while this laptop is on (local)
This is **not** 24/7 if the laptop sleeps/shuts down, but it auto-starts/restarts services after reboot/login.

1. **Run as Administrator** (required to create ONLOGON tasks): right‑click PowerShell → *Run as administrator*.
2. From repo root run:
   - `powershell -ExecutionPolicy Bypass -File "deploy\windows\install-adcs-autostart.ps1"`
   - `powershell -ExecutionPolicy Bypass -File "deploy\windows\start-adcs-now.ps1"`
3. Tasks created: `ADCS-MySQL` (XAMPP MariaDB), `ADCS-Backend` (Uvicorn :8000), `ADCS-Frontend` (preview :4173). They restart on failure (configured in the script).
4. Verify: `http://127.0.0.1:4173` and `http://127.0.0.1:8000/health`. Phone (same Wi‑Fi): `http://<your-IPv4>:4173` (IP may change with DHCP).
5. Remove: `powershell -ExecutionPolicy Bypass -File "deploy\windows\uninstall-adcs-autostart.ps1"` (no data deleted).

> Keep XAMPP/MySQL data and `ADCS/backend/.env`/uploads backed up. For true public 24/7, deploy the Docker stack to an always-on host.

## Local dev (unchanged)
- Backend: `ADCS/backend` venv + `uvicorn ... --host 0.0.0.0 --port 8000` (or 4173/5173 preview as configured).
- DB: local XAMPP/MariaDB per `.env`. Migrations: `alembic upgrade head`.

## Important caveats
- XAMPP local DB is **MariaDB 10.11** (MySQL-compatible). Use managed/private **MySQL** in production and migrate data if strict Oracle MySQL is required.
- Rotate any secrets previously exposed; never commit `.env` or credentials.
- Google OAuth redirect URIs and SMTP must be configured for the public URL.