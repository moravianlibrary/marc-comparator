# ── Builder stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends git libyaz5 \
    && rm -rf /var/lib/apt/lists/*

COPY sdk/ /sdk/
RUN pip install --no-cache-dir /sdk/

COPY app/requirements.app.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

ARG SYSTEM_VERSION
ARG SYSTEM_COMMIT
ENV SYSTEM_VERSION=${SYSTEM_VERSION}
ENV SYSTEM_COMMIT=${SYSTEM_COMMIT}

# libyaz5 is needed at runtime by aleph-nought (Z39.50)
RUN apt-get update \
    && apt-get install -y --no-install-recommends libyaz5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app

COPY app/access_control/ access_control/
COPY app/adapters/ adapters/
COPY app/auth/ auth/
COPY app/authority_linking/ authority_linking/
COPY app/catalog_records/ catalog_records/
COPY app/common/ common/
COPY app/comparison/ comparison/
COPY app/entities/ entities/
COPY app/maintenance/ maintenance/
COPY app/settings/ settings/
COPY app/system/ system/
COPY app/tasks/ tasks/
COPY app/validation/ validation/
COPY app/ws/ ws/
COPY app/app.py app.py
COPY app/app_lifespan.py app_lifespan.py
COPY app/config.py config.py
COPY app/alembic.ini alembic.ini
COPY app/migrations/ migrations/

# Exclude worker-specific files
RUN rm authority_linking/tasks.py \
    && rm catalog_records/tasks.py \
    && rm comparison/tasks.py \
    && rm maintenance/tasks.py \
    && rm validation/tasks.py

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
