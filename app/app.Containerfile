# Base image with Python 3.12
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install:
# - git - for git Python libraries
RUN apt-get update \
    && apt-get install -y git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy SDK code
COPY sdk/ /sdk/

# Copy requirements and install
COPY app/requirements.app.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Remove SDK code after installation
RUN rm -rf /sdk/

# Copy application code
COPY app/adapters/ adapters/
COPY app/auth/ auth/
COPY app/catalog/ catalog/
COPY app/entities/ entities/
COPY app/validation/ validation/
COPY app/app.py app.py
COPY app/app_lifespan.py app_lifespan.py
COPY app/config.py config.py

# Exclude workers-specific files
RUN rm catalog/tasks.py

# Command to run FastAPI app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
