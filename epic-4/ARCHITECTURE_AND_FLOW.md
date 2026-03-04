# Deployment Architecture & Flow

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Developer's Local Machine                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Code Changes → bash scripts/validate_before_push.sh            │
│       ↓            (tests, lint, format, validation)            │
│  Docker Image → bash scripts/test_docker_locally.sh             │
│       ↓            (build, start, test container)               │
│  Git Commit → git add . && git commit && git push              │
│       ↓                                                          │
└─────────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────────┐
│              GitHub Repository (main branch)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Webhook Trigger: Push to main detected                         │
│       ↓                                                          │
│  .github/workflows/epic4_workflow.yaml starts                   │
│       ↓                                                          │
└─────────────────────────────────────────────────────────────────┘
         ↓
┌──────────────────────────────┬──────────────────────────────────┐
│   Pull Request or PR Test      │      Push to Main (Production)  │
├──────────────────────────────┼──────────────────────────────────┤
│                              │                                  │
│  1. test-and-validate        │  1. test-and-validate            │
│     (Tests, Lint, Validate)  │     (Tests, Lint, Validate)      │
│           ↓ PASS             │           ↓ PASS                 │
│     2. build-and-push SKIP   │     2. build-and-push            │
│        (No Docker Push)       │        ├─ Docker build          │
│           ↓                   │        ├─ Push to ACR           │
│     ❌ STOP (No Deploy)       │        └─ Tag: latest + SHA     │
│                              │              ↓ SUCCESS           │
│                              │     3. deploy-to-container-app   │
│                              │        ├─ Update image           │
│                              │        └─ Verify deployment      │
│                              │              ↓ SUCCESS           │
│                              │     4. post-deployment-tests     │
│                              │        ├─ Health checks          │
│                              │        └─ Validation             │
│                              │              ↓ SUCCESS           │
│                              │    ✅ DEPLOYED TO PRODUCTION     │
│                              │                                  │
└──────────────────────────────┴──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────────┐
│          Azure Container Registry (docpulseresgistry)            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Image: drift-detect                                            │
│  Tags: latest, <commit-sha>, previous versions for rollback    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────────┐
│       Azure Container Apps (drift-detect in DocPulse RG)        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  🟢 Running Container                                           │
│  Port: 8000                                                     │
│  Health: ✓ Operational                                         │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Workflow Stages Detail

### Stage 1: test-and-validate
**Runs on**: All pushes and PRs
**Purpose**: Code quality and validation

```
test-and-validate
├── Checkout code
├── Setup Python 3.11
├── Install dependencies
├── Run pytest
├── Check formatting (Black)
├── Check linting (Flake8)
├── Create artifact directories
└── Run Epic-4 validation
    └─ Decision: PASS → Continue | FAIL → STOP
```

**Time Estimate**: 2-3 minutes

### Stage 2: build-and-push
**Runs on**: After test-and-validate passes
**Purpose**: Build and push Docker image to ACR

```
build-and-push
├── Checkout code
├── Login to Azure Container Registry
│   └─ Credentials: ACR_USERNAME + ACR_PASSWORD
├── Build Docker image
│   └─ From: Dockerfile
├── Tag image
│   ├─ docpulseresgistry.azurecr.io/drift-detect:latest
│   └─ docpulseresgistry.azurecr.io/drift-detect:<commit-sha>
├── Push to ACR
└── Verify push successful
    └─ Decision: SUCCESS → Continue | FAIL → STOP
```

**Time Estimate**: 3-5 minutes
**Storage**: ~500MB per image in ACR

### Stage 3: deploy-to-container-app
**Runs on**: After build-and-push passes, ONLY on main branch push
**Purpose**: Deploy image to Azure Container Apps

```
deploy-to-container-app
├── Checkout code
├── Azure Login
│   └─ Credentials: AZURE_CREDENTIALS (service principal)
├── Update Container App
│   ├── Image: drift-detect:latest
│   ├── Port: 8000
│   └─ Revision: Auto-created new revision
├── Verify update
└─ Decision: SUCCESS → Continue | FAIL → STOP
```

**Time Estimate**: 2-3 minutes
**Downtime**: ~1 minute during update

### Stage 4: post-deployment-tests
**Runs on**: After deploy succeeds
**Purpose**: Validate deployment health

```
post-deployment-tests
├── Checkout code
├── Wait 30 seconds for container startup
├── Health check
│   └─ GET /health endpoint
├── Container logs verification
├── Post-deployment validation
└─ Status: Complete
    └─ If failed: Log for review (non-blocking)
```

**Time Estimate**: 1-2 minutes

## Data Flow

### Configuration Data
```
GITHUB REPOSITORY
    ↓
.github/workflows/epic4_workflow.yaml
    ├─ Contains: ACR registry, image name, container app name
    ├─ References: GitHub Secrets
    │  ├─ ACR_USERNAME
    │  ├─ ACR_PASSWORD
    │  ├─ AZURE_CREDENTIALS
    │  └─ CONTAINER_APP_ENVIRONMENT
    └─ Outputs: Image tags in ACR
```

### Artifact Flow
```
Source Code
    ↓
Dockerfile
    ├─ Build Docker Image
    ├─ Size: ~500MB
    └─ Contains: Python 3.11 + Epic-4 application

Docker Image
    ↓
Azure Container Registry
    ├─ Repository: drift-detect
    │  ├─ Tag: latest (always latest)
    │  ├─ Tag: <commit-sha-1> (current)
    │  ├─ Tag: <commit-sha-2> (previous - for rollback)
    │  └─ Tag: <commit-sha-3> (older - for rollback)
    └─ Accessible to: Container App Environment

Container App
    ├─ Pulls Image: latest tag from ACR
    ├─ Starts Container
    ├─ Port Mapping: 8000 → 8000
    ├─ Volume Mounts: artifacts/ directory
    └─ Exposes: Public HTTPS URL
```

## Environment Variables at Each Stage

### Stage: test-and-validate
```
GITHUB_TOKEN          (from: GitHub)
REPO_OWNER           (from: GitHub)
REPO_NAME            (from: GitHub)
TARGET_BRANCH        (hardcoded: main)
COMMIT_SHA           (from: GitHub)
CI_RUN_ID            (from: GitHub)
```

### Stage: build-and-push
```
ACR_REGISTRY         (env: docpulseresgistry.azurecr.io)
IMAGE_NAME           (env: drift-detect)
IMAGE_TAG            (env: latest)
ACR_USERNAME         (from: GitHub Secret)
ACR_PASSWORD         (from: GitHub Secret)
GITHUB_SHA           (from: GitHub - commit SHA)
```

### Stage: deploy-to-container-app
```
CONTAINER_APP_NAME        (env: drift-detect)
RESOURCE_GROUP            (env: DocPulse)
CONTAINER_APP_ENVIRONMENT (from: GitHub Secret)
AZURE_CREDENTIALS         (from: GitHub Secret)
ACR_REGISTRY              (env: docpulseresgistry.azurecr.io)
IMAGE_NAME                (env: drift-detect)
IMAGE_TAG                 (env: latest)
```

### Stage: post-deployment-tests
```
CONTAINER_APP_NAME        (env: drift-detect)
RESOURCE_GROUP            (env: DocPulse)
CONTAINER_APP_URL         (from: GitHub Secret - optional)
```

## Error Handling & Rollback

### If Test Fails
```
❌ test-and-validate fails (tests or lint)
   └─ All subsequent stages STOP
   └─ No build, no ACR push, no deployment
   └─ Fix code locally and push again
```

### If Build/Push Fails
```
❌ build-and-push fails (Docker build or ACR push)
   └─ deploy-to-container-app STOPS
   └─ Previous version stays running in Container App
   └─ Check build logs and fix Docker configuration
```

### If Deployment Fails
```
❌ deploy-to-container-app fails
   └─ post-deployment-tests STOPS
   └─ Previous revision stays active (automatic rollback)
   └─ Check deployment logs and validate Container App config
```

### Manual Rollback
```
If current deployment causes issues:

az containerapp revision activate \
  --name drift-detect \
  --resource-group DocPulse \
  --revision drift-detect--<previous-revision>

Or redeploy with specific image tag:

az containerapp update \
  --name drift-detect \
  --resource-group DocPulse \
  --image docpulseresgistry.azurecr.io/drift-detect:<commit-sha>
```

## Monitoring & Observability

### What Gets Logged

#### GitHub Actions
- Workflow execution logs
- Each step's stdout/stderr
- Artifact upload/download details
- Job duration and status

#### Azure Container Registry
- Image push timestamps
- Image tags and layers
- Repository statistics
- Access logs

#### Azure Container Apps
- Container startup logs
- Application output logs
- Health check results
- Revision history
- Resource usage (CPU, memory)

### How to Monitor

1. **During Deployment**
   - GitHub Actions tab: Real-time workflow logs
   - Takes ~8-12 minutes total

2. **After Deployment**
   - Container App logs: `az containerapp logs show`
   - Container App revisions: `az containerapp revision list`
   - Web browser: Health endpoint check

3. **Issues**
   - GitHub Actions logs: Detailed error messages
   - Container App logs: Application errors
   - ACR: Image availability and health

## Cost Considerations

### About Azure Container Registry
- **Storage**: ~500MB per image × 3-5 versions = ~2-2.5GB
- **Cost**: ~$500/month for standard registry

### About Azure Container Apps
- **Compute**: Pay for vCPU-hours and memory-hours
- **Cost**: Depends on cpu/memory allocation

### How to Optimize
- Keep only essential image versions in ACR
- Set image retention policy: Delete old tags after 30 days
- Monitor resource usage and right-size Container App

---

**Diagram Created**: March 4, 2026
**For more details**: See [WORKFLOW_SETUP.md](WORKFLOW_SETUP.md)
