#!/bin/bash

# Setup Azure Authentication for GitHub Actions
# This script creates a Service Principal and outputs the JSON needed for the AZURE_CREDENTIALS GitHub Secret.

SUBSCRIPTION_ID=$(az account show --query id -o tsv)

if [ -z "$SUBSCRIPTION_ID" ]; then
  echo "Error: Please run 'az login' first."
  exit 1
fi

SP_NAME="github-actions-rally-deploy"

echo "Creating Service Principal '$SP_NAME' with Contributor access to subscription..."
SP_JSON=$(az ad sp create-for-rbac --name $SP_NAME --role contributor --scopes /subscriptions/$SUBSCRIPTION_ID --sdk-auth 2>/dev/null)

if [ $? -ne 0 ]; then
  echo "Failed to create Service Principal. Ensure you have sufficient permissions (Owner or User Access Administrator)."
  exit 1
fi

echo "================================================================="
echo "SUCCESS! Add the following JSON as a Repository Secret in GitHub"
echo "Secret Name: AZURE_CREDENTIALS"
echo "================================================================="
echo ""
echo "$SP_JSON"
echo ""
echo "================================================================="
