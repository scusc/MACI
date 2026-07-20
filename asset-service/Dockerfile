FROM python:3.11-slim

WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy the core library and the trip service
COPY maci-core ./maci-core
COPY trip-service ./trip-service

# Install the packages
RUN pip install --no-cache-dir ./maci-core ./trip-service

EXPOSE 8000

# Run uvicorn from the trip-service directory
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "trip-service"]
