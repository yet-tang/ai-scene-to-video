# GitHub Actions 镜像构建说明

## 快速开始

本项目已配置 GitHub Actions 自动构建 Docker 镜像，无需在 Coolify 服务器上构建。

### 1. 配置 GitHub Secrets

在 GitHub 仓库设置中添加：

```
Settings → Secrets and variables → Actions → New repository secret
```

| Secret 名称 | 说明 |
|------------|------|
| `VITE_API_BASE_URL` | 前端 API 地址 |
| `VITE_API_KEY` | 前端 API 密钥 |

### 2. 配置 Coolify 环境变量

```bash
# 镜像配置
DOCKER_REGISTRY=ghcr.io
DOCKER_IMAGE_PREFIX=<your-github-username>/ai-scene
IMAGE_TAG=latest

# 其他配置（数据库、Redis、S3等）见 .env.example
```

### 3. 部署

推送代码到 `main` 分支会自动触发构建：

```bash
git push origin main
```

等待 GitHub Actions 完成后，在 Coolify 中点击 **Redeploy**。

## 触发条件

- ✅ 推送到 `main` 或 `develop` 分支
- ✅ 推送版本标签 `v*` (如 `v1.2.0`)
- ✅ 创建 Pull Request (仅构建不推送)

## 生成的镜像

| 服务 | 镜像地址 |
|------|---------|
| Backend | `ghcr.io/<username>/ai-scene-backend:latest` |
| Engine | `ghcr.io/<username>/ai-scene-engine:latest` |
| Frontend | `ghcr.io/<username>/ai-scene-frontend:latest` |

## 镜像可见性

首次构建后，镜像默认为私有。需要设置为公开：

1. 进入 GitHub 仓库 → **Packages**
2. 点击对应包 → **Package settings**
3. 修改 **Visibility** 为 **Public**

或者在 Coolify 中配置 Registry Credentials 访问私有镜像。

## 详细文档

- [完整部署指南](./COOLIFY_DEPLOY.md)
- [CI/CD 详细说明](./docs/CI_CD_GUIDE.md)

## 故障排查

### 构建失败

查看 GitHub Actions 日志：`Actions → 失败的 Workflow → 点击查看详情`

### 镜像拉取失败

检查镜像可见性或配置 Coolify Registry Credentials。

### 更多问题

参考 [CI/CD 故障排查指南](./docs/CI_CD_GUIDE.md#故障排查)
