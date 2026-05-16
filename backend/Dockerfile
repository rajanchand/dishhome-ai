# ---- Base Layer ----
FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ---- Development Target ----
FROM base AS development
# Install dev tools if necessary, or just run with reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---- Production Target ----
FROM base AS production

COPY . .
RUN chmod +x scripts/start.sh

# Run as non-root user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Use the start script to handle migrations
ENTRYPOINT ["./scripts/start.sh"]
