
# syntax=docker/dockerfile:1

# ============================================================
# STAGE 1: BACKEND DEPENDENCIES AND SOURCE
# ============================================================
FROM python:3.11-slim AS backend-builder

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Copy backend source code
COPY backend/ ./backend/

# ============================================================
# STAGE 2: FRONTEND
# ============================================================
FROM node:18-alpine AS frontend-builder

WORKDIR /frontend

# Copy frontend source
COPY frontend/ ./

# Frontend is static HTML, CSS and JavaScript
RUN mkdir -p /frontend-built && cp -r . /frontend-built/

# ============================================================
# STAGE 3: FINAL PRODUCTION IMAGE
# ============================================================
FROM python:3.11-slim AS final

WORKDIR /app

# Install dependencies from backend builder
COPY --from=backend-builder /install /usr/local

# Copy backend source
COPY --from=backend-builder /app/backend ./backend

# Copy frontend static files
COPY --from=frontend-builder /frontend-built ./frontend

# Configure Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production
ENV APP_DEBUG=false

# Render provides the PORT environment variable
ENV PORT=10000

# Expose default Render port
EXPOSE 10000

# Start FastAPI application
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
