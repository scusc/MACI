#!/bin/bash
# ============================================================
# MACI Platform — Deploy using Azure ACR Build Tasks
# Builds images IN Azure (bypasses local Docker networking)
# ============================================================
set -e

REGISTRY="acrmacidev2025"
RESOURCE_GROUP="rg-maci-dev-eastus"
CLUSTER_NAME="aks-maci-dev"

echo "=== 🚀 Building & Pushing via Azure ACR Build Tasks ==="

echo "1. Logging into Azure ACR..."
az acr login --name $REGISTRY

echo "2. Building Auth Service in Azure ACR..."
az acr build --registry $REGISTRY \
  --image auth-service:latest \
  --file auth-service/Dockerfile \
  --platform linux/amd64 \
  . 2>&1

echo "3. Building Asset Service in Azure ACR..."
az acr build --registry $REGISTRY \
  --image asset-service:latest \
  --file asset-service/Dockerfile \
  --platform linux/amd64 \
  . 2>&1

echo "4. Building Group Service in Azure ACR..."
az acr build --registry $REGISTRY \
  --image group-service:latest \
  --file Dockerfile \
  --build-arg SERVICE_NAME=group-service \
  --platform linux/amd64 \
  . 2>&1

echo "5. Building Payment Service in Azure ACR..."
az acr build --registry $REGISTRY \
  --image payment-service:latest \
  --file Dockerfile \
  --build-arg SERVICE_NAME=payment-service \
  --platform linux/amd64 \
  . 2>&1

echo "6. Building API Gateway in Azure ACR..."
az acr build --registry $REGISTRY \
  --image api-gateway:latest \
  --file Dockerfile \
  --build-arg SERVICE_NAME=api-gateway \
  --platform linux/amd64 \
  . 2>&1

echo "7. Building Angular Frontend in Azure ACR..."
az acr build --registry $REGISTRY \
  --image frontend:latest \
  --file frontend/Dockerfile \
  --platform linux/amd64 \
  frontend/ 2>&1

echo "8. Setting AKS Context..."
az aks get-credentials --resource-group $RESOURCE_GROUP --name $CLUSTER_NAME --overwrite-existing

echo "9. Applying Kubernetes Manifests & Restarting Rollout..."
kubectl apply -f k8s/rally-platform.yaml
kubectl apply -f k8s/frontend.yaml
kubectl rollout restart deployment -n rally

echo "=== Getting Public Deployment Endpoints ==="
kubectl get svc -n rally

echo "=== 🎉 Azure Cloud Deployment Finished Successfully! ==="
