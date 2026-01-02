#!/bin/bash
set -e

echo "=== Starting Build Process ==="

# 1. Build Backend Image
echo "--- Building ai-scene-backend ---"
# Note: The Dockerfile uses multi-stage build, so it will compile the Java code inside the container.
# No need to run 'mvn package' locally.
docker build -t ai-scene-backend:latest ./backend

# 2. Build Engine Image
echo "--- Building ai-scene-engine ---"
docker build -t ai-scene-engine:latest ./engine

# 3. Build Frontend Image
echo "--- Building ai-scene-frontend ---"
docker build -t ai-scene-frontend:latest ./frontend

echo "=== Build Complete ==="
echo "Images built:"
echo "- ai-scene-backend:latest"
echo "- ai-scene-engine:latest"
echo "- ai-scene-frontend:latest"

echo "You can now run 'docker-compose -f docker-compose.coolify.yml up -d' to start the services locally for testing,"
echo "or push these images to a registry if needed."
