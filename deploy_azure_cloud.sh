#!/bin/bash
set -e

REGISTRY="acrmacidev123"
RESOURCE_GROUP="rg-maci-dev-eastus"
CLUSTER_NAME="aks-maci-dev"

echo "=== 🚀 Building & Publishing Rally Platform directly on Azure Cloud (ACR Cloud Build) ==="

echo "1. Building Auth Service on ACR Cloud..."
az acr build --registry $REGISTRY --image auth-service:latest -f auth-service/Dockerfile .

echo "2. Building Asset Service on ACR Cloud..."
az acr build --registry $REGISTRY --image asset-service:latest -f asset-service/Dockerfile .

echo "3. Building Group Service on ACR Cloud..."
az acr build --registry $REGISTRY --image group-service:latest --build-arg SERVICE_NAME=group-service -f Dockerfile .

echo "4. Building Payment Service on ACR Cloud..."
az acr build --registry $REGISTRY --image payment-service:latest --build-arg SERVICE_NAME=payment-service -f Dockerfile .

echo "5. Building API Gateway on ACR Cloud..."
az acr build --registry $REGISTRY --image api-gateway:latest --build-arg SERVICE_NAME=api-gateway -f Dockerfile .

echo "6. Building Angular Frontend on ACR Cloud..."
az acr build --registry $REGISTRY --image frontend:latest -f frontend/Dockerfile frontend/

echo "7. Setting AKS Context..."
az aks get-credentials --resource-group $RESOURCE_GROUP --name $CLUSTER_NAME --overwrite-existing

echo "8. Applying Kubernetes Manifests..."
kubectl apply -f k8s/rally-platform.yaml
kubectl apply -f k8s/frontend.yaml

echo "=== 🚀 Getting Public Deployment Endpoints ==="
kubectl get svc -n rally

echo "=== 🎉 Azure Cloud Deployment Finished! ==="
