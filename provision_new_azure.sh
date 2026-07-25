#!/bin/bash
# ============================================================
# MACI Platform — New Azure Account Infrastructure Provisioner
# Recreates all Azure resources in the new subscription
# ============================================================
set -e

# ── Resource Names (identical to old account) ───────────────
LOCATION="eastus"
RESOURCE_GROUP="rg-maci-dev-eastus"
ACR_NAME="acrmacidev123"
AKS_NAME="aks-maci-dev"
PSQL_SERVER="psql2-maci-dev"
PSQL_DB="rally"
PSQL_ADMIN="maciadmin"
REDIS_NAME="redis-maci-dev-123"
SB_NAMESPACE="sb-maci-dev-123"
SB_QUEUE="group-events"

# DB password (same as before so k8s manifests don't need changes)
PSQL_PASSWORD='p+Y[p2A.zuj.7efn5QT=YiHx7-NBZ]D$'

echo "========================================================"
echo "  MACI Platform — Azure Infrastructure Provisioner"
echo "  New Account: saichand.sunkara@icloud.com"
echo "========================================================"
echo ""

# Step 1: Login to new Azure account
echo "▶ Step 1: Logging in to new Azure account..."
az login --username saichand.sunkara@icloud.com --password 'Sc@250130' || {
  echo "Interactive login falling back..."
  az login
}

# Show active subscription
echo "✅ Logged in. Active subscription:"
az account show --query "{name:name, id:id, state:state}" -o table

# Step 2: Create Resource Group
echo ""
echo "▶ Step 2: Creating Resource Group: $RESOURCE_GROUP in $LOCATION..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
echo "✅ Resource group created."

# Step 3: Create Azure Container Registry (ACR)
echo ""
echo "▶ Step 3: Creating Azure Container Registry: $ACR_NAME..."
az acr create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$ACR_NAME" \
  --sku Basic \
  --admin-enabled true \
  --location "$LOCATION"
echo "✅ ACR created: $ACR_NAME.azurecr.io"

# Step 4: Create Azure Kubernetes Service (AKS)
echo ""
echo "▶ Step 4: Creating AKS Cluster: $AKS_NAME (this takes 5-10 mins)..."
az aks create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_NAME" \
  --node-count 2 \
  --node-vm-size Standard_B2s \
  --enable-managed-identity \
  --attach-acr "$ACR_NAME" \
  --location "$LOCATION" \
  --generate-ssh-keys \
  --network-plugin kubenet \
  --kubernetes-version 1.30
echo "✅ AKS cluster created."

# Step 5: Create Azure Database for PostgreSQL Flexible Server
echo ""
echo "▶ Step 5: Creating PostgreSQL Flexible Server: $PSQL_SERVER..."
az postgres flexible-server create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$PSQL_SERVER" \
  --location "$LOCATION" \
  --admin-user "$PSQL_ADMIN" \
  --admin-password "$PSQL_PASSWORD" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 16 \
  --public-access 0.0.0.0 \
  --yes

# Create the database
az postgres flexible-server db create \
  --resource-group "$RESOURCE_GROUP" \
  --server-name "$PSQL_SERVER" \
  --database-name "$PSQL_DB"
echo "✅ PostgreSQL server and database created."

# Step 6: Create Azure Cache for Redis
echo ""
echo "▶ Step 6: Creating Redis Cache: $REDIS_NAME..."
az redis create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$REDIS_NAME" \
  --location "$LOCATION" \
  --sku Basic \
  --vm-size C0
echo "✅ Redis cache created (may take a few minutes to be ready)."

# Step 7: Create Azure Service Bus Namespace + Queue
echo ""
echo "▶ Step 7: Creating Service Bus: $SB_NAMESPACE..."
az servicebus namespace create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$SB_NAMESPACE" \
  --location "$LOCATION" \
  --sku Basic

az servicebus queue create \
  --resource-group "$RESOURCE_GROUP" \
  --namespace-name "$SB_NAMESPACE" \
  --name "$SB_QUEUE"
echo "✅ Service Bus namespace and queue created."

# Step 8: Retrieve connection strings
echo ""
echo "▶ Step 8: Retrieving connection strings..."

PSQL_HOST="$PSQL_SERVER.postgres.database.azure.com"
PSQL_ENCODED_PASS=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$PSQL_PASSWORD'))")
DATABASE_URL="postgresql+asyncpg://$PSQL_ADMIN:$PSQL_ENCODED_PASS@$PSQL_HOST:5432/$PSQL_DB?ssl=require"

REDIS_KEY=$(az redis list-keys --resource-group "$RESOURCE_GROUP" --name "$REDIS_NAME" --query primaryKey -o tsv)
REDIS_HOST="$REDIS_NAME.redis.cache.windows.net"
REDIS_URL="redis://:$REDIS_KEY@$REDIS_HOST:6380"

SB_CONN=$(az servicebus namespace authorization-rule keys list \
  --resource-group "$RESOURCE_GROUP" \
  --namespace-name "$SB_NAMESPACE" \
  --name RootManageSharedAccessKey \
  --query primaryConnectionString -o tsv)

echo ""
echo "════════════════════════════════════════════════════"
echo "  NEW CONNECTION STRINGS (save these!)"
echo "════════════════════════════════════════════════════"
echo "DATABASE_URL: $DATABASE_URL"
echo "REDIS_URL: $REDIS_URL"
echo "SERVICE_BUS: $SB_CONN"
echo ""

# Step 9: Update Kubernetes manifests with new connection strings
echo "▶ Step 9: Updating k8s/rally-platform.yaml with new connection strings..."
python3 - <<PYEOF
import re

with open("k8s/rally-platform.yaml", "r") as f:
    content = f.read()

db_url = "$DATABASE_URL"
redis_url = "$REDIS_URL"
sb_conn = """$SB_CONN"""

# Replace DATABASE_URL values
content = re.sub(
    r'(- name: DATABASE_URL\n\s+value: ")[^"]*(")',
    r'\g<1>' + db_url + r'\g<2>',
    content
)
# Replace REDIS_URL values
content = re.sub(
    r'(- name: REDIS_URL\n\s+value: ")[^"]*(")',
    r'\g<1>' + redis_url + r'\g<2>',
    content
)
# Replace SERVICE_BUS_CONNECTION_STRING values
content = re.sub(
    r'(- name: SERVICE_BUS_CONNECTION_STRING\n\s+value: ")[^"]*(")',
    r'\g<1>' + sb_conn + r'\g<2>',
    content
)

with open("k8s/rally-platform.yaml", "w") as f:
    f.write(content)

print("k8s/rally-platform.yaml updated successfully.")
PYEOF

# Step 10: Get AKS credentials
echo ""
echo "▶ Step 10: Getting AKS credentials..."
az aks get-credentials --resource-group "$RESOURCE_GROUP" --name "$AKS_NAME" --overwrite-existing
echo "✅ kubectl context set to $AKS_NAME."

echo ""
echo "════════════════════════════════════════════════════"
echo "  ✅ INFRASTRUCTURE PROVISIONING COMPLETE!"
echo "  Next: Run deploy_azure_cloud.sh to build & push"
echo "  containers and apply Kubernetes manifests."
echo "════════════════════════════════════════════════════"
