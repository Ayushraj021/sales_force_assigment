# Feast Feature Server Dockerfile
FROM python:3.11-slim

WORKDIR /feast

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Feast and dependencies
COPY requirements.txt /feast/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy feature store configuration and definitions
COPY feature_store.yaml /feast/
COPY features/ /feast/features/
COPY data_sources/ /feast/data_sources/

# Expose feature server port
EXPOSE 6566

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:6566/health || exit 1

# Run feature server
CMD ["feast", "serve", "-h", "0.0.0.0", "-p", "6566"]
