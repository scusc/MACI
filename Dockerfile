# Base image
FROM python:3.11-slim

ARG SERVICE_NAME
ENV SERVICE_NAME=${SERVICE_NAME}

WORKDIR /app

COPY maci-core /app/maci-core
COPY ${SERVICE_NAME}/app /app/app

RUN pip install --no-cache-dir uvicorn /app/maci-core

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
