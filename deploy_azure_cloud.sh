#!/bin/bash
set -e

REGISTRY="acrmacidev2025.azurecr.io"
RESOURCE_GROUP="rg-maci-dev-eastus"
CLUSTER_NAME="aks-maci-dev"

echo "=== 🚀 Building & Pushing Production AMD64 Containers for Azure AKS Cluster ==="

echo "1. Logging into Azure ACR..."
az acr login --name acrmacidev2025

echo "2. Building & Pushing Auth Service (linux/amd64)..."
docker build --platform linux/amd64 -t $REGISTRY/auth-service:latest -f auth-service/Dockerfile .
docker push $REGISTRY/auth-service:latest

echo "3. Building & Pushing Asset Service (linux/amd64)..."
docker build --platform linux/amd64 -t $REGISTRY/asset-service:latest -f asset-service/Dockerfile .
docker push $REGISTRY/asset-service:latest

echo "4. Building & Pushing Group Service (linux/amd64)..."
docker build --platform linux/amd64 --build-arg SERVICE_NAME=group-service -t $REGISTRY/group-service:latest -f Dockerfile .
docker push $REGISTRY/group-service:latest

echo "5. Building & Pushing Payment Service (linux/amd64)..."
docker build --platform linux/amd64 --build-arg SERVICE_NAME=payment-service -t $REGISTRY/payment-service:latest -f Dockerfile .
docker push $REGISTRY/payment-service:latest

echo "6. Building & Pushing API Gateway (linux/amd64)..."
docker build --platform linux/amd64 --build-arg SERVICE_NAME=api-gateway -t $REGISTRY/api-gateway:latest -f Dockerfile .
docker push $REGISTRY/api-gateway:latest

echo "7. Building & Pushing Angular Frontend (linux/amd64)..."
docker build --platform linux/amd64 -t $REGISTRY/frontend:latest -f frontend/Dockerfile frontend/
docker push $REGISTRY/frontend:latest

echo "8. Setting AKS Context..."
az aks get-credentials --resource-group $RESOURCE_GROUP --name $CLUSTER_NAME --overwrite-existing

echo "9. Applying Kubernetes Manifests & Restarting Rollout..."
kubectl apply -f k8s/rally-platform.yaml
kubectl apply -f k8s/frontend.yaml
kubectl rollout restart deployment -n rally

echo "=== 🚀 Getting Public Deployment Endpoints ==="
kubectl get svc -n rally

echo "=== 🎉 Azure Cloud Deployment Finished Successfully! ==="
