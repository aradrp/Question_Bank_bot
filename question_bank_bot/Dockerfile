# ─────────────────────────────────────────────────────────────
#  Dockerfile – Question Bank Bot
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

# System dependencies (needed by psutil)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create runtime directories (volumes will overlay these at runtime)
RUN mkdir -p uploads logs database

# Non-root user for security
RUN useradd -r -u 1001 botuser \
    && chown -R botuser:botuser /app
USER botuser

CMD ["python", "bot.py"]
