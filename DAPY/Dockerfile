FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./
COPY README.md ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -e .

# Copy application code
COPY dapy/ ./dapy/

# Create directories for data persistence
RUN mkdir -p /app/data /app/snapshots /app/logs

# Set up git config (will be overridden by volume mount)
RUN git config --global user.name "DAPY" && \
    git config --global user.email "dapy@localhost"

# Expose port for daemon mode
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD dapy version || exit 1

# Default command
CMD ["dapy", "--help"]
