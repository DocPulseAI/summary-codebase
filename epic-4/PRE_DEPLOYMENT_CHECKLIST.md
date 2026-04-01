# Pre-Deployment Checklist

Complete this checklist before committing and pushing code to ensure smooth deployment to Render.

## 🔍 Pre-Commit Validation

### 1. Code Quality Checks
- [ ] Run tests: `pytest tests/ -v`
- [ ] Check formatting: `black --check epic4/ tests/`
- [ ] Run linter: `flake8 epic4/ tests/`
- [ ] Review any linting warnings/errors
- [ ] Fix any issues found

### 2. Application Validation
- [ ] Run: `python validate_epic4.py`
- [ ] Verify validation report and R2 configuration

### 3. Docker Image Testing
- [ ] Run: `bash scripts/test_docker_locally.sh`
- [ ] Verify image builds successfully
- [ ] Confirm container starts without errors

## 🚀 Deployment Readiness

### 4. GitHub Secrets Configuration (For CI)
Before pushing, ensure these secrets are configured in GitHub Actions to pass validations:
- [ ] `R2_ACCOUNT_ID` - Cloudflare R2 Account ID
- [ ] `R2_ACCESS_KEY_ID` - Cloudflare R2 Access Key
- [ ] `R2_SECRET_ACCESS_KEY` - Cloudflare R2 Secret Key

### 5. Render Configuration Verification
- [ ] Review `render.yaml` ensuring `rootDir` is set to `epic-4`
- [ ] Verify environment variables are configured in the Render Dashboard

## 🔄 Push to Repository

Once all items are checked, push your changes to GitHub:

```bash
git add .
git commit -m "Deploying to Render"
git push origin main
```

Render will automatically detect the changes and begin the deployment process. Monitor the deployment in your Render Dashboard.
