FROM python:3.11-slim as builder

WORKDIR /app

# System deps needed by some pipecat audio packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install numpy wheel first to avoid build-from-source
RUN pip install --no-cache-dir --only-binary=:all: numpy && \
    pip install --no-cache-dir -r requirements.txt \
        --extra-index-url https://pypi.fury.io/daily/

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 receptionist && chown -R receptionist:receptionist /app
USER receptionist

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"

# Run with gunicorn for production (changes uvicorn to multi-worker setup)
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
