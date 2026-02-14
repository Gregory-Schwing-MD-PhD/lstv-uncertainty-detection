#!/bin/bash
# Build and push LSTV Uncertainty Detection Docker container
# Usage: ./docker/build_and_push.sh
#
# OPTIMIZED BUILD: Uses pip-only (no Conda) for faster builds
# - python-gdcm instead of conda install gdcm (10x faster)
# - pylibjpeg for DICOM compression support
# - Smaller image size, faster build times

set -euo pipefail

# Configuration
DOCKER_USERNAME="go2432"
IMAGE_NAME="lstv-uncertainty"
TAG="latest"
FULL_IMAGE="${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================================"
echo "LSTV Uncertainty Detection - Docker Build & Push"
echo "================================================================"
echo ""
echo "Target: ${FULL_IMAGE}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker not found${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

echo -e "${GREEN}✓${NC} Docker found: $(docker --version)"

# Check if logged in to Docker Hub
if ! docker info | grep -q "Username"; then
    echo ""
    echo -e "${YELLOW}⚠ Not logged in to Docker Hub${NC}"
    echo "Attempting login..."
    docker login
fi

echo -e "${GREEN}✓${NC} Docker Hub authentication confirmed"
echo ""

# Navigate to docker directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
DOCKER_DIR="${PROJECT_DIR}/docker"

cd "$DOCKER_DIR"

echo "================================================================"
echo "Building Docker image..."
echo "================================================================"
echo ""

# Build the image
docker build \
    --platform linux/amd64 \
    -t "${FULL_IMAGE}" \
    -f Dockerfile \
    .

build_exit=$?

if [ $build_exit -ne 0 ]; then
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Build successful!${NC}"
echo ""

# Get image size
IMAGE_SIZE=$(docker images "${FULL_IMAGE}" --format "{{.Size}}")
echo "Image size: ${IMAGE_SIZE}"
echo ""

# Test the image
echo "================================================================"
echo "Testing Docker image..."
echo "================================================================"
echo ""

docker run --rm "${FULL_IMAGE}" python --version
docker run --rm "${FULL_IMAGE}" python -c "import torch; print(f'PyTorch {torch.__version__}')"
docker run --rm "${FULL_IMAGE}" python -c "import pydicom; print(f'pydicom {pydicom.__version__}')"

echo ""
echo -e "${GREEN}✓ Image tests passed${NC}"
echo ""

# Ask for confirmation to push
read -p "Push to Docker Hub? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Skipping push"
    echo ""
    echo "Image built successfully: ${FULL_IMAGE}"
    echo "To push later, run: docker push ${FULL_IMAGE}"
    exit 0
fi

echo ""
echo "================================================================"
echo "Pushing to Docker Hub..."
echo "================================================================"
echo ""

docker push "${FULL_IMAGE}"

push_exit=$?

if [ $push_exit -ne 0 ]; then
    echo -e "${RED}✗ Push failed${NC}"
    exit 1
fi

echo ""
echo "================================================================"
echo -e "${GREEN}✓ SUCCESS!${NC}"
echo "================================================================"
echo ""
echo "Image pushed to Docker Hub: ${FULL_IMAGE}"
echo ""
echo "To use in Singularity:"
echo "  singularity pull lstv-uncertainty.sif docker://${FULL_IMAGE}"
echo ""
echo "To pull on another machine:"
echo "  docker pull ${FULL_IMAGE}"
echo ""
echo "================================================================"
