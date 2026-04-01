# Epic-4 Workflow Setup

## Overview
This workflow automates the Continuous Integration (CI) and Continuous Deployment (CD) for the Epic-4 Drift Engine.
- **CI**: GitHub Actions runs tests, linters, and validates the configuration.
- **CD**: Render natively handles building the Docker image and deploying the web service automatically.

## Required Secrets

### GitHub Repo Secrets (For CI)
These are needed for the GitHub Actions tests to succeed.
```
R2_ACCOUNT_ID                 # Cloudflare R2 Account ID
R2_ACCESS_KEY_ID              # Cloudflare R2 Access Key
R2_SECRET_ACCESS_KEY          # Cloudflare R2 Secret Key
```

### Render Dashboard Secrets (For CD)
In your Render Dashboard, ensure the same Cloudflare R2 storage secrets and other required application configurations are set.

## Deployment Process
1. Push changes to the `main` branch.
2. GitHub Actions will run the `.github/workflows/epic4_workflow.yaml` CI pipeline to validate the code.
3. Render will detect the push and automatically deploy the updated `Dockerfile` using the blueprint configurations in `render.yaml` based in the `epic-4` subdirectory.

## Troubleshooting
If a deployment fails:
1. **GitHub Actions logs**: Check the CI tabs to see if tests failed.
2. **Render Dashboard**: Check the Build and Deploy logs in the Render console if the application doesn't start properly.
