# ========================================================
# Dockerfile for Fraud Detection Dashboard
# Tech Stack: Python 3.11-slim + Flask + Gunicorn WSGI
# ========================================================

FROM python:3.11-slim

# Prevent python from buffering stdout/stderr and writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

# Set work directory
WORKDIR /app

# Install system dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose Flask / Gunicorn port
EXPOSE 5000

# Docker healthcheck querying /health endpoint
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run with Gunicorn production WSGI server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "wsgi:app"]
