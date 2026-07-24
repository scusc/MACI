#!/bin/bash
set -e

REGISTRY="acrmacidev123.azurecr.io"

echo "=== 🚀 Building and Pushing Rally Microservices to Azure ACR ($REGISTRY) ==="

echo "1. Building & Pushing Auth Service..."
docker build -t $REGISTRY/auth-service:latest -f auth-service/Dockerfile .
docker push $REGISTRY/auth-service:latest

echo "2. Building & Pushing Asset Service..."
docker build -t $REGISTRY/asset-service:latest -f asset-service/Dockerfile .
docker push $REGISTRY/asset-service:latest

echo "3. Building & Pushing Group Service..."
docker build --build-arg SERVICE_NAME=group-service -t $REGISTRY/group-service:latest -f Dockerfile .
docker push $REGISTRY/group-service:latest

echo "4. Building & Pushing Payment Service..."
docker build --build-arg SERVICE_NAME=payment-service -t $REGISTRY/payment-service:latest -f Dockerfile .
docker push $REGISTRY/payment-service:latest

echo "5. Building & Pushing API Gateway..."
docker build --build-arg SERVICE_NAME=api-gateway -t $REGISTRY/api-gateway:latest -f Dockerfile .
docker push $REGISTRY/api-gateway:latest

echo "6. Building & Pushing Angular Frontend..."
cd frontend
docker build -t $REGISTRY/frontend:latest -f Dockerfile .
docker push $REGISTRY/frontend:latest
cd ..

echo "=== 🎉 All Rally container images pushed to Azure ACR successfully! ==="
