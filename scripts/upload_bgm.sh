#!/bin/bash

# BGM Upload Script for AI Scene to Video
# This script helps upload BGM files to S3 and update configuration

set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check required environment variables
if [ -z "$S3_STORAGE_ENDPOINT" ] || [ -z "$S3_STORAGE_ACCESS_KEY" ] || [ -z "$S3_STORAGE_SECRET_KEY" ]; then
    echo "❌ Error: S3 storage configuration missing"
    echo "Please set S3_STORAGE_ENDPOINT, S3_STORAGE_ACCESS_KEY, S3_STORAGE_SECRET_KEY in .env"
    exit 1
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ Error: AWS CLI not installed"
    echo "Install: brew install awscli (macOS) or apt install awscli (Ubuntu)"
    exit 1
fi

# Function to upload a single BGM file
upload_bgm() {
    local file_path=$1
    local filename=$(basename "$file_path")
    local object_key="bgm/${filename}"
    
    echo "📤 Uploading ${filename} to S3..."
    
    aws s3 cp "$file_path" "s3://${S3_STORAGE_BUCKET}/${object_key}" \
        --endpoint-url="${S3_STORAGE_ENDPOINT}" \
        --content-type="audio/mpeg" \
        --acl public-read
    
    local public_url="${S3_STORAGE_PUBLIC_URL}/${object_key}"
    echo "✅ Uploaded: ${public_url}"
    echo "${public_url}"
}

# Main script
if [ $# -eq 0 ]; then
    echo "Usage: $0 <bgm_file1.mp3> [bgm_file2.mp3] ..."
    echo ""
    echo "Example:"
    echo "  $0 warm-piano-01.mp3 cozy-acoustic-02.mp3"
    echo ""
    echo "This will:"
    echo "  1. Upload BGM files to S3 bucket"
    echo "  2. Print public URLs to configure in application.yml"
    exit 1
fi

echo "🎵 AI Scene to Video - BGM Upload Tool"
echo "========================================"
echo ""

# Upload all files and collect URLs
urls=()
for file in "$@"; do
    if [ ! -f "$file" ]; then
        echo "⚠️  Warning: File not found: ${file}"
        continue
    fi
    
    url=$(upload_bgm "$file")
    urls+=("$url")
done

# Print configuration snippet
if [ ${#urls[@]} -gt 0 ]; then
    echo ""
    echo "✅ All BGM files uploaded successfully!"
    echo ""
    echo "📝 Add these URLs to backend/src/main/resources/application.yml:"
    echo ""
    echo "app:"
    echo "  bgm:"
    echo "    auto-select: true"
    echo "    builtin-urls:"
    for url in "${urls[@]}"; do
        echo "      - ${url}"
    done
    echo ""
    echo "Or set in Coolify environment variables (YAML format):"
    echo "APP_BGM_BUILTIN_URLS: ${urls[0]}"
    for i in "${!urls[@]}"; do
        if [ $i -gt 0 ]; then
            echo "  - ${urls[$i]}"
        fi
    done
fi
