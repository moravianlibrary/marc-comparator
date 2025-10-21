# Base image with Python 3.12
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

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

# Copy requirements and install
COPY app/requirements.worker.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Remove SDK code after installation
RUN rm -rf /sdk/

# Copy application code
COPY app/adapters/ adapters/
COPY app/auth/ auth/
COPY app/catalog/ catalog/
COPY app/entities/ entities/
COPY app/config.py config.py

# Exclude app-specific files
RUN rm adapters/dependencies.py
RUN find . -type f -name "controller.py" -delete
RUN find . -type f -name "service.py" -delete

# Command to run Celery
CMD ["celery", "-A", "adapters.tasks", "worker", "--loglevel=info"]
