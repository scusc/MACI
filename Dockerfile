# Base image
FROM python:3.11-slim as builder

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# The SERVICE_NAME argument tells the Dockerfile which microservice to build
ARG SERVICE_NAME
ENV SERVICE_NAME=${SERVICE_NAME}

# Copy the shared core library
COPY maci-core /app/maci-core

# Copy the specific service requirements
COPY ${SERVICE_NAME}/requirements.txt /app/requirements.txt

# Install maci-core normally (not editable) and service dependencies
# We remove "-e ../maci-core" from requirements if it exists and install it directly
RUN sed -i '/-e \.\.\/maci-core/d' /app/requirements.txt || true
RUN pip install --no-cache-dir /app/maci-core && \
    pip install --no-cache-dir -r /app/requirements.txt

# Final image
FROM python:3.11-slim

ARG SERVICE_NAME
ENV SERVICE_NAME=${SERVICE_NAME}
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy the service code
COPY ${SERVICE_NAME}/app /app/app

EXPOSE 80

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
