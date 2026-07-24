# Base image
FROM python:3.11-slim

ARG SERVICE_NAME
ENV SERVICE_NAME=${SERVICE_NAME}

WORKDIR /app

COPY maci-core /app/maci-core
COPY ${SERVICE_NAME}/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir uvicorn httpx /app/maci-core -r /app/requirements.txt

COPY ${SERVICE_NAME}/app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
