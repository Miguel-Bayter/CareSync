# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# System deps needed to compile psycopg2-binary (if needed at build time)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Hugging Face Spaces uses port 7860; override with PORT env var if needed
ENV PORT=7860

# Non-root user for security
RUN useradd --no-create-home --shell /bin/false appuser \
 && chown -R appuser /app
USER appuser

EXPOSE $PORT

# Use exec form so signals propagate correctly (graceful shutdown)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1"]
