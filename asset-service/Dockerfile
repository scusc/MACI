FROM python:3.11-slim

WORKDIR /app

COPY maci-core ./maci-core
COPY asset-service ./asset-service

RUN pip install --no-cache-dir ./maci-core ./asset-service

COPY asset-service/app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
