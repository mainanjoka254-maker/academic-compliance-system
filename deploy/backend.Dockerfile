# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for mysqlclient/pymysql crypto and healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential default-libmysqlclient-dev curl \
 && rm -rf /var/lib/apt/lists/*

COPY ADCS/backend/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

COPY ADCS/backend /app

# Uploads (mount a volume in production)
RUN mkdir -p /app/private_uploads

EXPOSE 8000

# Run migrations then start (safe: upgrade head is idempotent). Restart policy handled by orchestrator.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]