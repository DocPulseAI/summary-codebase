# Pre-Deployment Checklist

Complete this checklist before committing and pushing code to ensure smooth deployment to ACR and Azure Container Apps.

## 🔍 Pre-Commit Validation

### 1. Code Quality Checks
- [ ] Run tests: `pytest tests/ -v`
- [ ] Check formatting: `black --check epic4/ tests/`
- [ ] Run linter: `flake8 epic4/ tests/`
- [ ] Review any linting warnings/errors
- [ ] Fix any issues found

### 2. Application Validation
- [ ] Run: `python validate_epic4.py`
- [ ] Review validation report
- [ ] Verify all configurations are correct
- [ ] Check artifact generation (if applicable)

### 3. Automated Validation Script
- [ ] Run: `bash scripts/validate_before_push.sh`
- [ ] Verify all checks pass
- [ ] Review any warnings
- [ ] Address any failures

### 4. Docker Image Testing
- [ ] Run: `bash scripts/test_docker_locally.sh`
- [ ] Verify image builds successfully
- [ ] Confirm container starts without errors
- [ ] Check container logs for any issues
- [ ] Verify memory/CPU usage is reasonable

### 5. Configuration Review
- [ ] Verify all environment variables are documented
- [ ] Check Dockerfile is up-to-date
- [ ] Confirm requirements.txt has all dependencies
- [ ] Review any recent dependency changes

## 📋 Git Commit Preparation

### 6. Git Status Check
- [ ] Run: `git status`
- [ ] Review all changes: `git diff`
- [ ] Remove any unnecessary files
- [ ] Verify no secrets in code: `git diff` for passwords/keys
- [ ] Check no large binary files added

### 7. Commit Message
- [ ] Write clear, descriptive commit message
- [ ] Include reference to related issues/PRs
- [ ] Use conventional commit format if applicable

## 🚀 Deployment Readiness

### 8. GitHub Secrets Configuration
Before pushing, ensure these secrets are configured in GitHub:
- [ ] `EPIC4_AZURE_CLIENT_ID` - Azure AD Application (Client) ID
- [ ] `EPIC4_AZURE_TENANT_ID` - Azure AD Directory (Tenant) ID
- [ ] `EPIC4_AZURE_SUBSCRIPTION_ID` - Azure Subscription ID
- [ ] `EPIC4_REGISTRY_USERNAME` - Azure Container Registry username
- [ ] `EPIC4_REGISTRY_PASSWORD` - Azure Container Registry password/token

To add secrets:
1. Go to GitHub repository → Settings
2. Navigate to Secrets and Variables → Actions
3. Click "New repository secret"
4. Add each secret listed above

### 9. Azure Resources Verification
- [ ] Verify ACR exists: `docpulseresgistry.azurecr.io`
- [ ] Confirm Container App exists: `drift-detect` in resource group `DocPulse`
- [ ] Check Azure service principal has required permissions
- [ ] Verify service principal has Contributor role on DocPulse resource group
- [ ] OIDC federated credential is configured

### 10. Workflow Configuration Review
- [ ] Review `.github/workflows/epic4_workflow.yaml`
- [ ] Verify trigger is set to: `push` on `main` branch
- [ ] Verify ACR registry name: `docpulseresgistry.azurecr.io`
- [ ] Verify image name: `drift-detect`
- [ ] Verify container app name: `drift-detect`
- [ ] Verify resource group: `DocPulse`

## ⚙️ Azure Setup (One-time)

### 11. Create Azure Service Principal with OIDC
Run these commands once:

```bash
# Create service principal
az ad sp create-for-rbac \
  --name "epic4-github-actions" \
  --role contributor \
  --scopes /subscriptions/{YOUR_SUBSCRIPTION_ID}/resourceGroups/DocPulse
```

This will output something like:
```json
{
  "appId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "displayName": "epic4-github-actions",
  "password": "...",
  "tenant": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

Save these values - you'll need them in the next step.

### 12. Configure OIDC Federated Credentials

```bash
# Get the service principal app ID from the output above
APP_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

# Create OIDC federated credential for your GitHub repo
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-epic4",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:YOUR_GITHUB_ORG/YOUR_GITHUB_REPO:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

Replace:
- `YOUR_GITHUB_ORG` with your GitHub organization or username
- `YOUR_GITHUB_REPO` with your repository name

### 13. Add GitHub Secrets \
  --role contributor \
  --scopes /subscriptions/{YOUR_SUBSCRIPTION_ID}/resourceGroups/DocPulse
```

This will output JSON - copy as `AZURE_CREDENTIALS` secret.

### 12. Grant ACR Pull/Push Permissions

```bash
# Get service principal ID
SP_ID=$(az ad sp list --display-name github-actions-epic4 --query "[0].id" -o tsv)

# Assign AcrPush role to ACR
az role assignment create \
  --assignee $SP_ID \
  --role AcrPush \
  --scope /subscriptions/{SUBSCRIPTION_ID}/resourceGroups/DocPulse/providers/Microsoft.ContainerRegistry/registries/docpulseresgistry
```

### 13. Grant Container Apps Deployment Permission

```bash
# Grant Contributor role to Container Apps
az role assignment create \
  --assignee $SP_ID \
  --role "Contributor" \
  --scope /subscriptions/{SUBSCRIPTION_ID}/resourceGroups/DocPulse
```

## 📝 Final Review

### 14. Documentation Update
- [ ] Update README if deployment process changed
- [ ] Document any new environment variables
- [ ] Update troubleshooting guides if needed
- [ ] Review this checklist - update if items missing

### 15. Ready to Push
- [ ] All checks above completed
- [ ] No failed tests or validations
- [ ] Secrets configured in GitHub
- [ ] Azure resources verified
- [ ] Commit message written and reviewed

## 🔄 Push to Repository

Once all items are checked:

```bash
git add .
git commit -m "Your descriptive commit message"
git push origin main
```

## 📊 Monitoring After Push

### Workflow Execution
1. Go to GitHub repository → Actions tab
2. Watch the workflow run:
   - **test-and-validate** - Should complete first
   - **build-and-push** - Builds and pushes Docker image
   - **deploy-to-container-app** - Deploys to Azure
   - **post-deployment-tests** - Validates deployment

### Verify Deployment Success
```bash
# Check Container App status
az containerapp show \
  --name drift-detect \
  --resource-group DocPulse \
  --query properties.latestRevisionFqdn -o tsv

# Check recent deployments
az containerapp revision list \
  --name drift-detect \
  --resource-group DocPulse \
  --query "[0].{Name:name, CreatedTime:properties.createdTime, Status:properties.provisioning.state}"
```

### View Deployment Logs
```bash
az containerapp logs show \
  --name drift-detect \
  --resource-group DocPulse \
  --follow
```

## 🆘 Troubleshooting

If something fails:

1. **Check GitHub Actions logs** - Click the failed job for detailed error messages
2. **Review ACR image** - Verify image was pushed: `docker images`
3. **Check Container App logs** - See deployment errors
4. **Verify Azure credentials** - Ensure service principal has correct permissions
5. **Test locally first** - Use `scripts/test_docker_locally.sh` to validate

## 📞 Support

For issues:
1. Check [WORKFLOW_SETUP.md](WORKFLOW_SETUP.md) for detailed configuration
2. Review workflow logs in GitHub Actions
3. Check Azure portal for resource status
4. Run local validation scripts for diagnostics
