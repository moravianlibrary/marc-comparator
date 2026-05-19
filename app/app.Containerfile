# Base image with Python 3.12
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Declare build args
ARG SYSTEM_VERSION
ARG SYSTEM_COMMIT

# Set build args as environment variables
ENV SYSTEM_VERSION=${SYSTEM_VERSION}
ENV SYSTEM_COMMIT=${SYSTEM_COMMIT}

# Set working directory
WORKDIR /app

# Install:
# - git - for git Python libraries
# - libyaz5 - for Z39.50 support
RUN apt-get update \
    && apt-get install -y git libyaz5 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy SDK code
COPY sdk/ /sdk/

# Install SDK and app requirements
RUN pip install --no-cache-dir /sdk/
COPY app/requirements.app.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Remove SDK code after installation
RUN rm -rf /sdk/

# Copy application code
COPY app/access_control/ access_control/
COPY app/adapters/ adapters/
COPY app/auth/ auth/
COPY app/authority_linking/ authority_linking/
COPY app/catalog_records/ catalog_records/
COPY app/common/ common/
COPY app/comparison/ comparison/
COPY app/entities/ entities/
COPY app/settings/ settings/
COPY app/system/ system/
COPY app/tasks/ tasks/
COPY app/validation/ validation/
COPY app/app.py app.py
COPY app/app_lifespan.py app_lifespan.py
COPY app/config.py config.py

# Exclude workers-specific files
RUN rm authority_linking/tasks.py
RUN rm catalog_records/tasks.py
RUN rm comparison/tasks.py
RUN rm validation/tasks.py

# Command to run FastAPI app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
