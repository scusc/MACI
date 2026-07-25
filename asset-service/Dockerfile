FROM python:3.11-slim

WORKDIR /app

COPY maci-core ./maci-core
COPY asset-service/requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install --default-timeout=600 --retries 10 --no-cache-dir uvicorn httpx ./maci-core -r requirements.txt

COPY asset-service/app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
