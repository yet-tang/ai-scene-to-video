#!/bin/bash
# ============================================
# Coolify 镜像标签自动更新脚本
# ============================================
# 用途：在 GitHub Actions 构建完成后，自动更新 Coolify 的 IMAGE_TAG
# 
# 使用方法：
# 1. 在 GitHub Actions 的最后一步调用此脚本
# 2. 需要配置 COOLIFY_API_URL 和 COOLIFY_API_TOKEN
#
# 示例：
#   bash update_coolify_tag.sh main-abc1234
# ============================================

set -e

# 参数检查
if [ -z "$1" ]; then
    echo "错误：缺少镜像标签参数"
    echo "使用方法: $0 <IMAGE_TAG>"
    echo "示例: $0 main-abc1234"
    exit 1
fi

IMAGE_TAG=$1
COOLIFY_API_URL="${COOLIFY_API_URL:-}"
COOLIFY_API_TOKEN="${COOLIFY_API_TOKEN:-}"
COOLIFY_PROJECT_ID="${COOLIFY_PROJECT_ID:-}"

# 检查必需的环境变量
if [ -z "$COOLIFY_API_URL" ]; then
    echo "错误：未设置 COOLIFY_API_URL 环境变量"
    echo "示例：export COOLIFY_API_URL=https://your-coolify.com"
    exit 1
fi

if [ -z "$COOLIFY_API_TOKEN" ]; then
    echo "错误：未设置 COOLIFY_API_TOKEN 环境变量"
    echo "请在 Coolify 控制台生成 API Token"
    exit 1
fi

if [ -z "$COOLIFY_PROJECT_ID" ]; then
    echo "错误：未设置 COOLIFY_PROJECT_ID 环境变量"
    exit 1
fi

echo "=== 更新 Coolify 镜像标签 ==="
echo "项目ID: $COOLIFY_PROJECT_ID"
echo "新标签: $IMAGE_TAG"

# 调用 Coolify API 更新环境变量
# 注意：具体 API 路径需根据 Coolify 版本调整
response=$(curl -s -X PATCH \
    "${COOLIFY_API_URL}/api/v1/projects/${COOLIFY_PROJECT_ID}/env" \
    -H "Authorization: Bearer ${COOLIFY_API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"IMAGE_TAG\": \"${IMAGE_TAG}\"}")

echo "API 响应: $response"

# 触发重新部署
echo "触发 Coolify 重新部署..."
curl -s -X POST \
    "${COOLIFY_API_URL}/api/v1/projects/${COOLIFY_PROJECT_ID}/deploy" \
    -H "Authorization: Bearer ${COOLIFY_API_TOKEN}"

echo "=== 更新完成 ==="
