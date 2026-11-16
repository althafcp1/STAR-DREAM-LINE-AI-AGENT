# syntax=docker/dockerfile:1

# ---------- Build stage (backend) ----------
FROM python:3.11-slim AS backend-builder
WORKDIR /app
# Install build dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# Copy backend source
COPY backend/ ./
# Copy config and .env example
COPY backend/app/config.py ./backend/app/
COPY backend/.env.example ./backend/.env.example

# ---------- Build stage (frontend) ----------
FROM node:18-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/ .
# Install any build tools if needed (assume static only, skip npm)
# For a real project you would run npm install && npm run build
# Here we just copy files
RUN cp -r . /frontend-built

# ---------- Final image ----------
FROM python:3.11-slim AS final
WORKDIR /app
# Copy backend built artifacts
COPY --from=backend-builder /app /app
# Copy frontend static files into backend static directory
COPY --from=frontend-builder /frontend-built /app/frontend
# Expose the FastAPI port
EXPOSE 8000
# Runtime environment variables (override in production)
ENV APP_ENV=production
ENV APP_DEBUG=false
# Start the server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

