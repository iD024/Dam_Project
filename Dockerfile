# Production Dockerfile for Dam-Break Simulation Backend
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Install system dependencies for geospatial libraries (GDAL, GEOS, PROJ)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgdal-dev \
    gdal-bin \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application code and sample/demo data
COPY backend/ /app/backend/
COPY data/ /app/data/

# Ensure output and demo directories exist
RUN mkdir -p /app/data/outputs /app/data/demo

EXPOSE 8000

# Run uvicorn using shell form to allow dynamic $PORT binding for Render/Railway/CloudRun
CMD sh -c "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"
