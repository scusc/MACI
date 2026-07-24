#!/bin/bash
set -e

REGISTRY="acrmacidev123.azurecr.io"

echo "=== 🚀 Building AMD64 Production Containers for Azure AKS Cluster ==="

echo "1. Building Frontend (linux/amd64)..."
docker build --platform linux/amd64 -t $REGISTRY/frontend:latest -f frontend/Dockerfile frontend/
docker push $REGISTRY/frontend:latest

echo "2. Building Auth Service (linux/amd64)..."
docker build --platform linux/amd64 -t $REGISTRY/auth-service:latest -f auth-service/Dockerfile .
docker push $REGISTRY/auth-service:latest

echo "3. Building Asset Service (linux/amd64)..."
docker build --platform linux/amd64 -t $REGISTRY/asset-service:latest -f asset-service/Dockerfile .
docker push $REGISTRY/asset-service:latest

echo "4. Building Group Service (linux/amd64)..."
docker build --platform linux/amd64 --build-arg SERVICE_NAME=group-service -t $REGISTRY/group-service:latest -f Dockerfile .
docker push $REGISTRY/group-service:latest

echo "5. Building Payment Service (linux/amd64)..."
docker build --platform linux/amd64 --build-arg SERVICE_NAME=payment-service -t $REGISTRY/payment-service:latest -f Dockerfile .
docker push $REGISTRY/payment-service:latest

echo "6. Building API Gateway (linux/amd64)..."
docker build --platform linux/amd64 --build-arg SERVICE_NAME=api-gateway -t $REGISTRY/api-gateway:latest -f Dockerfile .
docker push $REGISTRY/api-gateway:latest

echo "=== 🎉 All AMD64 images successfully built and pushed to Azure ACR! ==="
