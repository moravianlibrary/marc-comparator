# ── Builder stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends git libyaz5 \
    && rm -rf /var/lib/apt/lists/*

# requirements.worker.txt is uv's fully-resolved transitive closure, so pip must not
# re-resolve on top of it: uv pins the git deps by commit while the SDK's metadata
# names the same packages by tag, and pip rejects that as conflicting direct URLs.
# --no-deps installs exactly what uv locked, which is also what makes it reproducible.
COPY app/requirements.worker.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --no-deps -r /tmp/requirements.txt

# The SDK's own dependencies are already in the export above.
COPY sdk/ /sdk/
RUN pip install --no-cache-dir --no-deps /sdk/

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
COPY app/periodic_sync/ periodic_sync/
COPY app/reports/ reports/
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
