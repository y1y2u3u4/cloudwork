# =====================================
# CloudWork Dockerfile
# =====================================
# Multi-stage build for smaller image size

FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    expect \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x (required for Claude Code CLI)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# =====================================
# Production stage
# =====================================
FROM base AS production

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create directories for runtime data
RUN mkdir -p /app/data /app/workspace /app/logs

# Set working directory for Claude CLI
WORKDIR /app

# Health check (optional)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the bot
CMD ["python", "-m", "src.bot.main"]

# =====================================
# Development stage (optional)
# =====================================
FROM base AS development

WORKDIR /app

# Install dev dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir pytest pytest-cov pytest-asyncio

# Copy everything for development
COPY . .

# Development command
CMD ["python", "-m", "src.bot.main"]
