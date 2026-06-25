FROM python:3.11-slim

WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy the core library and the auth service
COPY maci-core ./maci-core
COPY auth-service ./auth-service

# Install the packages
RUN pip install --no-cache-dir ./maci-core ./auth-service

EXPOSE 8000

# Run uvicorn from the auth-service directory
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "auth-service"]
