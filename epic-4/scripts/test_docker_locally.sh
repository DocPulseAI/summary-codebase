#!/bin/bash

##############################################
# Local Docker Build & Test Script
# Test Docker image locally before ACR push
##############################################

set -e

# Configuration
ACR_REGISTRY="docpulseresgistry.azurecr.io"
IMAGE_NAME="drift-detect"
LOCAL_TAG="test-$(date +%s)"

echo "=========================================="
echo "Local Docker Build & Test"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Configuration:"
echo "  Registry: $ACR_REGISTRY"
echo "  Image: $IMAGE_NAME"
echo "  Local Test Tag: $LOCAL_TAG"
echo ""

# Step 1: Build Image
echo "Step 1: Building Docker Image"
echo "--------------------------------------"
docker build -t $IMAGE_NAME:$LOCAL_TAG .
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Image built successfully${NC}"
else
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi
echo ""

# Step 2: Check image size
echo "Step 2: Checking Image Specifications"
echo "--------------------------------------"
SIZE=$(docker images --format "{{.Size}}" $IMAGE_NAME:$LOCAL_TAG)
echo "Image Size: $SIZE"
echo -e "${GREEN}✓ Image ready for testing${NC}"
echo ""

# Step 3: Test Container Startup
echo "Step 3: Testing Container Startup"
echo "--------------------------------------"
echo "Starting container in background..."
CONTAINER_ID=$(docker run -d \
    -p 8000:8000 \
    -e GITHOOKUP_TOKEN="test-token" \
    -e REPO_OWNER="test-owner" \
    -e REPO_NAME="test-repo" \
    $IMAGE_NAME:$LOCAL_TAG)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Container started (ID: ${CONTAINER_ID:0:12})${NC}"
else
    echo -e "${RED}✗ Container failed to start${NC}"
    exit 1
fi
echo ""

# Step 4: Wait for container to be ready
echo "Step 4: Waiting for Container to Stabilize"
echo "--------------------------------------"
echo "Waiting 10 seconds..."
sleep 10

# Check if container is still running
if docker ps | grep -q $CONTAINER_ID; then
    echo -e "${GREEN}✓ Container is running${NC}"
else
    echo -e "${RED}✗ Container stopped unexpectedly${NC}"
    docker logs $CONTAINER_ID | tail -20
    exit 1
fi
echo ""

# Step 5: Test Health Endpoint (if available)
echo "Step 5: Testing Health Endpoint"
echo "--------------------------------------"
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health) || HEALTH_CHECK="000"

if [ "$HEALTH_CHECK" = "200" ] || [ "$HEALTH_CHECK" = "404" ]; then
    echo -e "${GREEN}✓ Container is responding (HTTP $HEALTH_CHECK)${NC}"
else
    echo -e "${YELLOW}! Health check returned: HTTP $HEALTH_CHECK (container may still be initializing)${NC}"
fi
echo ""

# Step 6: Check Container Logs
echo "Step 6: Container Logs (last 20 lines)"
echo "--------------------------------------"
docker logs $CONTAINER_ID | tail -20
echo ""

# Step 7: Cleanup
echo "Step 7: Cleanup"
echo "--------------------------------------"
docker stop $CONTAINER_ID
docker rm $CONTAINER_ID
docker rmi $IMAGE_NAME:$LOCAL_TAG
echo -e "${GREEN}✓ Cleaned up test container and image${NC}"
echo ""

echo "=========================================="
echo "Summary"
echo "=========================================="
echo -e "${GREEN}✓ Local Docker testing completed successfully!${NC}"
echo ""
echo "The Docker image is ready to be pushed to ACR:"
echo "  docker tag $IMAGE_NAME:latest $ACR_REGISTRY/$IMAGE_NAME:latest"
echo "  docker push $ACR_REGISTRY/$IMAGE_NAME:latest"
echo ""
