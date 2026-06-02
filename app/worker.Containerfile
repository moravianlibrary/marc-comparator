# ── Builder stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends git libyaz5 \
    && rm -rf /var/lib/apt/lists/*

COPY sdk/ /sdk/
RUN pip install --no-cache-dir /sdk/

COPY app/requirements.worker.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# libyaz5 is needed at runtime by aleph-nought (Z39.50)
RUN apt-get update \
    && apt-get install -y --no-install-recommends libyaz5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app

COPY app/adapters/ adapters/
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
COPY app/config.py config.py

# Exclude app-specific files
RUN rm adapters/dependencies.py \
    && find . -type f -name "controller.py" -delete \
    && find . -type f -name "service.py" -delete

CMD ["celery", "-A", "adapters.tasks", "worker", "--loglevel=info"]
