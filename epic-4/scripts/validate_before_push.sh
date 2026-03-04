#!/bin/bash

##############################################
# Local Pre-Deployment Validation Script
# Run this before pushing to ensure everything is ready
##############################################

set -e

echo "=========================================="
echo "Epic-4 Pre-Deployment Validation Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FAILED=0

# Function to print status
check_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
        FAILED=$((FAILED + 1))
    fi
}

echo "Step 1: Checking Python Dependencies"
echo "--------------------------------------"
pip list | grep -E "pytest|black|flake8" > /dev/null
check_status $? "Required tools installed"
echo ""

echo "Step 2: Running Tests"
echo "--------------------------------------"
pytest tests/ -v --tb=short 2>&1 | tail -20
check_status $? "Tests passed"
echo ""

echo "Step 3: Code Quality Checks"
echo "--------------------------------------"
echo "Black (formatting)..."
black --check epic4/ tests/ 2>&1 | head -10
BLACK_STATUS=$?
check_status $BLACK_STATUS "Code formatting is correct"

echo ""
echo "Flake8 (linting)..."
flake8 epic4/ tests/ --max-line-length=120 --count 2>&1 | tail -5
FLAKE8_STATUS=$?
check_status $FLAKE8_STATUS "Code linting passed"
echo ""

echo "Step 4: Docker Image Build Validation"
echo "--------------------------------------"
docker build -t drift-detect:test . > /dev/null 2>&1
check_status $? "Docker image builds successfully"
echo ""

echo "Step 5: Checking Application Configuration"
echo "--------------------------------------"
if [ -f "epic4/config.py" ]; then
    echo -e "${GREEN}✓ Config file exists${NC}"
else
    echo -e "${RED}✗ Config file missing${NC}"
    FAILED=$((FAILED + 1))
fi
echo ""

echo "Step 6: Validating Epic-4 Setup"
echo "--------------------------------------"
if [ -f "validate_epic4.py" ]; then
    python validate_epic4.py 2>&1 | tail -10
    check_status $? "Epic-4 validation passed"
else
    echo -e "${YELLOW}! Validation script not found${NC}"
fi
echo ""

echo "Step 7: Checking Repository Status"
echo "--------------------------------------"
if [ -d ".git" ]; then
    echo -e "${GREEN}✓ Git repository found${NC}"

    # Check for uncommitted changes
    if [ -z "$(git status --porcelain)" ]; then
        echo -e "${GREEN}✓ Working directory clean${NC}"
    else
        echo -e "${YELLOW}! Uncommitted changes detected:${NC}"
        git status --short | head -10
    fi
else
    echo -e "${RED}✗ Not a git repository${NC}"
    FAILED=$((FAILED + 1))
fi
echo ""

echo "Step 8: Verifying Required Secrets"
echo "--------------------------------------"
if [ -z "$ACR_USERNAME" ]; then
    echo -e "${YELLOW}! ACR_USERNAME not set in environment${NC}"
fi

if [ -z "$ACR_PASSWORD" ]; then
    echo -e "${YELLOW}! ACR_PASSWORD not set in environment${NC}"
fi

if [ -z "$AZURE_CREDENTIALS" ]; then
    echo -e "${YELLOW}! AZURE_CREDENTIALS not set in environment${NC}"
fi

echo -e "${GREEN}✓ Secrets check complete (set GitHub Secrets if not local testing)${NC}"
echo ""

echo "=========================================="
echo "Summary"
echo "=========================================="

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All checks passed! Ready to push/deploy.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. git add ."
    echo "  2. git commit -m 'Your message'"
    echo "  3. git push origin main"
    echo ""
    exit 0
else
    echo -e "${RED}$FAILED check(s) failed. Please fix issues before pushing.${NC}"
    echo ""
    exit 1
fi
