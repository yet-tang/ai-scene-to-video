#!/bin/bash
set -e

# Get version info
IMAGE_TAG=${IMAGE_TAG:-latest}
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILD_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "=== Build Version Info ==="
echo "Image Tag: $IMAGE_TAG"
echo "Git Commit: $GIT_COMMIT"
echo "Build Time: $BUILD_TIME"
echo "=========================="

# Export for docker-compose
export IMAGE_TAG
export GIT_COMMIT
export BUILD_TIME

# Build images with version info
docker compose -f docker-compose.coolify.yaml build \
  --build-arg IMAGE_TAG="$IMAGE_TAG" \
  --build-arg GIT_COMMIT="$GIT_COMMIT" \
  --build-arg BUILD_TIME="$BUILD_TIME" \
  "$@"

echo ""
echo "✅ Build completed with version info:"
echo "   IMAGE_TAG=$IMAGE_TAG"
echo "   GIT_COMMIT=$GIT_COMMIT"
echo "   BUILD_TIME=$BUILD_TIME"
