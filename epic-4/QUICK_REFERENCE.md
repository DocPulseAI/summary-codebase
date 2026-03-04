# Quick Reference Guide

## 🎯 Pre-Deployment Commands

### Run All Validations
```bash
bash scripts/validate_before_push.sh
```

### Test Docker Image Locally
```bash
bash scripts/test_docker_locally.sh
```

### Run Tests Only
```bash
pytest tests/ -v
```

### Check Code Quality
```bash
black --check epic4/ tests/
flake8 epic4/ tests/
```

### Validate Epic-4
```bash
python validate_epic4.py
```

## 📦 Docker Commands

### Build Docker Image
```bash
docker build -t drift-detect:latest .
```

### Run Container Locally
```bash
docker run -d \
  -p 8000:8000 \
  -e GITHUB_TOKEN="your-token" \
  -e REPO_OWNER="owner" \
  -e REPO_NAME="repo" \
  drift-detect:latest
```

### View Container Logs
```bash
docker logs <container-id>
```

## 🔐 Azure Container Registry Commands

### Login to ACR
```bash
az acr login --name docpulseresgistry
```

### Tag Image for ACR
```bash
docker tag drift-detect:latest docpulseresgistry.azurecr.io/drift-detect:latest
docker tag drift-detect:latest docpulseresgistry.azurecr.io/drift-detect:$(git rev-parse --short HEAD)
```

### Push to ACR
```bash
docker push docpulseresgistry.azurecr.io/drift-detect:latest
```

### List Images in ACR
```bash
az acr repository list --name docpulseresgistry
az acr repository show-tags --name docpulseresgistry --repository drift-detect
```

## 🚀 Azure Container App Commands

### Check Deployment Status
```bash
az containerapp show \
  --name drift-detect \
  --resource-group DocPulse \
  --query "properties.latestRevisionFqdn" -o tsv
```

### View Recent Revisions
```bash
az containerapp revision list \
  --name drift-detect \
  --resource-group DocPulse
```

### View Logs
```bash
az containerapp logs show \
  --name drift-detect \
  --resource-group DocPulse \
  --follow
```

### Update Image Manually
```bash
az containerapp update \
  --name drift-detect \
  --resource-group DocPulse \
  --image docpulseresgistry.azurecr.io/drift-detect:latest
```

### Rollback to Previous Version
```bash
az containerapp revision activate \
  --name drift-detect \
  --resource-group DocPulse \
  --revision drift-detect--<revision-number>
```

## 📝 Git Commands

### Check Status Before Commit
```bash
git status
git diff
```

### Commit Changes
```bash
git add .
git commit -m "feat: update workflow for ACR and container app deployment"
```

### Push to Main
```bash
git push origin main
```

### View Recent Commits
```bash
git log --oneline -10
```

## 🔑 GitHub Secrets Setup

### Required Secrets in GitHub
1. `ACR_USERNAME` - Azure Container Registry username
2. `ACR_PASSWORD` - Azure Container Registry password
3. `AZURE_CREDENTIALS` - Service principal JSON
4. `CONTAINER_APP_ENVIRONMENT` - Container App Environment name

### View Secrets (from command line)
```bash
# Cannot view secrets directly, but can test authentication
az acr login --username $ACR_USERNAME --password $ACR_PASSWORD
```

### Add Secret to GitHub (via CLI)
```bash
gh secret set ACR_USERNAME -b "your-username"
gh secret set ACR_PASSWORD -b "your-password"
```

## 🔍 Monitoring & Debugging

### Monitor Workflow in GitHub
1. Go to: Actions tab in GitHub
2. Select: "Epic-4 Automation with ACR & Container App Deploy"
3. Click the latest run
4. Click on a job to see detailed logs

### Debug Failed Deployment
```bash
# Check ACR image exists
az acr repository show \
  --name docpulseresgistry \
  --repository drift-detect

# Check Container App configuration
az containerapp show \
  --name drift-detect \
  --resource-group DocPulse

# Check Container App logs
az containerapp logs show \
  --name drift-detect \
  --resource-group DocPulse \
  --tail 100
```

## 📋 Typical Workflow

### Before Committing
```bash
# 1. Validate everything
bash scripts/validate_before_push.sh

# 2. Test Docker locally
bash scripts/test_docker_locally.sh

# 3. Check git status
git status
git diff
```

### Committing Changes
```bash
git add .
git commit -m "feat: update deployment workflow"
git push origin main
```

### Monitoring Deployment
1. Open GitHub Actions tab
2. Watch workflow progress
3. Check Container App runs successfully
4. Verify logs show no errors

## 🆘 Common Issues & Fixes

### Issue: Docker image won't build
```bash
# Clean Docker cache and rebuild
docker system prune -a
docker build -t drift-detect:latest .
```

### Issue: ACR authentication fails
```bash
# Try logging in manually
az acr login --name docpulseresgistry

# Check credentials
echo $ACR_USERNAME
echo $ACR_PASSWORD
```

### Issue: Container App not updating
```bash
# Force restart the app
az containerapp update \
  --name drift-detect \
  --resource-group DocPulse \
  --force-restart
```

### Issue: Health check failing
```bash
# View full container logs
az containerapp logs show \
  --name drift-detect \
  --resource-group DocPulse \
  --tail 50

# Check Container App settings
az containerapp show \
  --name drift-detect \
  --resource-group DocPulse
```

## 📚 Important Files

- **Workflow**: `.github/workflows/epic4_workflow.yaml`
- **Dockerfile**: `Dockerfile`
- **Setup Guide**: `WORKFLOW_SETUP.md`
- **Checklist**: `PRE_DEPLOYMENT_CHECKLIST.md`
- **Validation Script**: `scripts/validate_before_push.sh`
- **Docker Test Script**: `scripts/test_docker_locally.sh`

## 🎓 Key Configuration Values

| Item | Value |
|------|-------|
| ACR Registry | docpulseresgistry.azurecr.io |
| Image Name | drift-detect |
| Image Tag | latest |
| Container App | drift-detect |
| Resource Group | DocPulse |
| App Port | 8000 |

---

For detailed information, see:
- [WORKFLOW_SETUP.md](WORKFLOW_SETUP.md) - Complete workflow configuration
- [PRE_DEPLOYMENT_CHECKLIST.md](PRE_DEPLOYMENT_CHECKLIST.md) - Full pre-deployment checklist
