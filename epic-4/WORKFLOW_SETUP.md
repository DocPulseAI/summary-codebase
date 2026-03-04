# Epic-4 GitHub Actions Workflow Setup

## Overview
This workflow automates the build, test, and deployment process for the Epic-4 application to Azure Container Registry (ACR) and Azure Container Apps using a single, unified job.

## Workflow Job

### **build-and-deploy** (Triggered on push to main)
Single job that handles everything:
- Sets up Python 3.11 environment
- Installs dependencies
- Runs tests with comprehensive validation
- Performs linting and formatting checks
- Validates Epic-4 configuration
- Authenticates with Azure (OIDC)
- Logs into Azure Container Registry
- Builds Docker image
- Pushes to ACR with two tags:
  - `latest` (latest stable)
  - `<commit-sha>` (specific version)
- Deploys to Azure Container Apps
- Creates new revision with timestamp suffix
- Verifies deployment completion

## Configuration

### Trigger Events
```yaml
on:
  push:
    branches: [main]
    paths:
      - "**"
      - ".github/workflows/epic4_workflow.yaml"
  workflow_dispatch:  # Allow manual trigger
```

### Required Secrets (Add to GitHub Repo Settings → Secrets and Variables → Actions)

#### Azure OIDC Secrets (Recommended - More Secure)
```
EPIC4_AZURE_CLIENT_ID         # Azure AD Application (Client) ID
EPIC4_AZURE_TENANT_ID         # Azure AD Directory (Tenant) ID
EPIC4_AZURE_SUBSCRIPTION_ID   # Azure Subscription ID
```

#### Azure Container Registry Secrets
```
EPIC4_REGISTRY_USERNAME       # Your ACR username
EPIC4_REGISTRY_PASSWORD       # Your ACR password/token
```

Example Azure Credentials format:
```json

## Setting Up Azure OIDC Authentication

### Step 1: Create Azure Service Principal
```bash
az ad sp create-for-rbac \
  --name "epic4-github-actions" \
  --role contributor \
  --scopes /subscriptions/{YOUR_SUBSCRIPTION_ID}/resourceGroups/DocPulse
```

### Step 2: Note the Output
The command will output:
```json
{
  "clientId": "...",        ← EPIC4_AZURE_CLIENT_ID
  "clientSecret": "...",
  "subscriptionId": "...",  ← EPIC4_AZURE_SUBSCRIPTION_ID
  "tenantId": "..."         ← EPIC4_AZURE_TENANT_ID
}
```

### Step 3: Configure OIDC Federated Credentials
```bash
# Get your GitHub repository ID
GITHUB_REPO_ID="owner/repo"

# Get the service principal object ID
SP_OBJECT_ID=$(az ad sp list --display-name epic4-github-actions --query "[0].id" -o tsv)

# Create federated credential
az ad app federated-credential create \
  --id $(az ad sp list --display-name epic4-github-actions --query "[0].appId" -o tsv) \
  --parameters '{
    "name": "github-epic4",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'$GITHUB_REPO_ID':ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

### Step 4: Add Secrets to GitHub
1. Go to GitHub Repository → Settings → Secrets and variables → Actions
2. Add these secrets:
   - `EPIC4_AZURE_CLIENT_ID` - From service principal clientId
   - `EPIC4_AZURE_TENANT_ID` - From service principal tenantId
   - `EPIC4_AZURE_SUBSCRIPTION_ID` - From service principal subscriptionId
   - `EPIC4_REGISTRY_USERNAME` - Your ACR username
   - `EPIC4_REGISTRY_PASSWORD` - Your ACR password/token

## Workflow Execution

### Automatic Triggers
- **Push to main branch** - Runs full pipeline (validate → build → push → deploy)
- **Manual trigger** - Use workflow_dispatch from Actions tab

### Manual Deployment
To manually trigger:
1. Go to Actions tab in GitHub
2. Click "Trigger auto deployment for drift-detect"
3. Click "Run workflow"
4. Confirm trigger

## What Happens During Deployment

The workflow validates the following **before and during deployment**:

1. ✅ **Code Quality & Tests**
   - Python tests with pytest
   - Code formatting check (Black)
   - Linting (Flake8)
   - Docker image builds successfully

3. ✅ **ACR Push**
   - Image successfully pushed to Azure Container Registry
   - Both `latest` and commit SHA tags applied

4. ✅ **Deployment Verification**
   - Container App updated with new image
   - Health checks pass

## Environment Variables for Container App

When deploying, ensure these environment variables are set in Container App:

```
GITHUB_TOKEN                         # GitHub API token
REPO_OWNER                          # Repository owner
REPO_NAME                           # Repository name
TARGET_BRANCH                       # Target branch (default: main)
PYTHONDONTWRITEBYTECODE             # Set to 1
PYTHONUNBUFFERED                    # Set to 1
```

## Monitoring & Logs

### View Workflow Logs
1. Go to Actions tab in GitHub repository
2. Select the latest workflow run
3. Click on each job to see detailed logs

### View Container App Logs
```bash
az containerapp logs show \
  --name drift-detect \
  --resource-group DocPulse \
  --follow
```

### Monitor ACR Image
```bash
az acr repository show \
  --name docpulseresgistry \
  --repository drift-detect
```

## Troubleshooting

### Authentication Failures
- Verify `AZURE_CREDENTIALS` is properly formatted JSON
- Check ACR username/password are correct
- Ensure service principal has contributor role

### Image Push Failures
- Check ACR is accessible from GitHub Actions IP
- Verify ACR credentials haven't expired
- Check Docker image size isn't exceeding limits

### Deployment Failures
- Ensure Container App environment exists
- Check resource group name spelling: `DocPulse`
- Verify Container App configuration supports port 8000
- Review Container App environment variables

### Health Check Issues
- Ensure application exposes `/health` endpoint
- Check network security groups allow outbound HTTPS
- Verify DNS resolution for Container App FQDN

## Rollback Procedure

If deployment causes issues, rollback to previous version:

```bash
az containerapp update \
  --name drift-detect \
  --resource-group DocPulse \
  --image docpulseresgistry.azurecr.io/drift-detect:PREVIOUS_TAG
```

## Next Steps

1. Add required secrets to GitHub repository
2. Create Azure service principal for authentication
3. Test the workflow on a feature branch (will run validate only)
4. Once verified, merge to main for full deployment
