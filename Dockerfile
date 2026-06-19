# Multi-stage build keeps the final image small.
# Stage 1: install dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

# Copy dependency files first to leverage Docker layer caching
COPY requirements.txt requirements-dev.txt ./

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


# Stage 2: lean runtime image
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy project source
COPY src/ ./src/
COPY app.py pyproject.toml ./

# Create data directory (mounted as a volume at runtime)
RUN mkdir -p /app/data

# Expose Streamlit port
EXPOSE 8501

# Default command: run the collector.
# Override in docker-compose to run the dashboard instead.
CMD ["python", "-m", "src.main"]