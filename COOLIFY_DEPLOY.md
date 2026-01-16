# Coolify 部署指南

本指南将帮助你将 `AI Scene to Video` 项目部署到 Coolify 平台。

## 部署架构说明

**新部署方式（推荐）**: 使用 GitHub Actions 自动构建镜像，Coolify 直接拉取预构建镜像，减轻服务器负担。

### 架构对比

| 项目 | 旧方式：源码部署 | 新方式：镜像部署 |
|------|-----------------|------------------|
| 构建位置 | Coolify 服务器 | GitHub Actions |
| 服务器负载 | 高（Maven + NPM + Docker） | 低（仅拉取镜像）|
| 构建时间 | 10-15 分钟 | 2-3 分钟（服务器端）|
| 适用场景 | 临时测试 | 生产环境 |

---

## 1. 准备工作

### 1.1 基础设施

确保你已经拥有：
1. Coolify 实例的访问权限。
2. 自部署的 PostgreSQL 数据库连接信息。
3. 自部署的 Redis 连接信息。
4. Supabase (或兼容 S3) 的存储桶信息。
5. 阿里云 DashScope API Key (用于 Qwen-VL 和 Qwen-Plus)。

### 1.2 GitHub 配置

#### 步骤 1：启用 GitHub Container Registry (GHCR)

1. 登录 [GitHub Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens)
2. 创建一个 **Classic Token** 或 **Fine-grained token**
3. 勾选权限：
   - `write:packages`
   - `read:packages`
   - `delete:packages` (可选)
4. 保存 Token 备用

#### 步骤 2：配置 GitHub Repository Secrets

在你的 GitHub 仓库中：
1. 进入 **Settings → Secrets and variables → Actions**
2. 点击 **New repository secret** 添加以下配置：

```bash
# Frontend 构建参数（必填）
VITE_API_BASE_URL=https://your-api-domain.com
VITE_API_KEY=your_frontend_api_key

# Coolify Webhook（自动触发部署，必填）
COOLIFY_WEBHOOK_URL=https://your-coolify.com/api/v1/deploy/webhooks/xxxxxxxx
```

**如何获取 Coolify Webhook URL**：
1. 登录 Coolify 控制台
2. 进入你的项目 → **Webhooks** 页面
3. 复制 **Deploy Webhook URL**
4. 将 URL 粘贴到 GitHub Secrets 中

**注意**: `GITHUB_TOKEN` 无需手动配置，GitHub Actions 会自动注入。

#### 步骤 3：配置自动部署

本项目已配置 **GitHub Actions 自动触发 Coolify 部署**，无需手动操作。

**工作流程**：
1. 推送代码到 `main` 分支
2. GitHub Actions 自动构建所有服务的 Docker 镜像
3. 镜像推送到 GHCR (GitHub Container Registry)
4. **自动调用 Coolify Webhook，触发重新部署**
5. Coolify 拉取最新的 `latest` 镜像并重启服务

**验证自动部署**：
- 推送代码后，进入 GitHub Actions 查看 `trigger-coolify-deploy` 步骤
- 应该看到 "✅ Coolify 部署已触发成功"

#### 步骤 4：触发首次构建

推送代码到 `main` 或 `develop` 分支即可自动触发构建：

```bash
git add .
git commit -m "feat: add GitHub Actions CI/CD"
git push origin main
```

等待 GitHub Actions 完成后，镜像将推送到 `ghcr.io/<your-username>/ai-scene-backend:latest`。

---

## 2. Coolify 配置

### 2.1 创建项目

1. 在 Coolify 面板中，点击 **"New Resource"**。
2. 选择 **"Docker Compose"** 类型。
3. 选择 **"Public Repository"** 或 **"Private Repository (with GitHub App)"**（如果是私有仓库）。
4. 输入你的 Git 仓库地址。
5. **关键步骤**：
   - 在 **"Docker Compose Location"** 输入：`docker-compose.coolify.yaml`
   - 确保 **Build Pack** 选为 **"Docker Compose"**

**服务说明**：
- `ai-scene-backend`: Java 后端服务
- `ai-scene-engine`: Python AI 引擎服务
- `ai-scene-frontend`: Vue 前端服务 (Nginx)

### 2.2 配置环境变量

在 Coolify 的 **"Environment Variables"** 区域添加以下变量：

#### 镇像配置（必填）

```bash
# Docker 镜像仓库配置
DOCKER_REGISTRY=ghcr.io
DOCKER_IMAGE_PREFIX=<your-github-username>/ai-scene
IMAGE_TAG=latest  # 或使用 main, develop, v1.0.0 等标签
```

**重要说明**：
- `DOCKER_IMAGE_PREFIX` 必须与 GitHub Actions 中的设置一致
- 默认为 `ghcr.io/<github-username>/ai-scene`
- 如果你的仓库是 `https://github.com/johndoe/ai-scene-to-video`，则设置：
  ```bash
  DOCKER_IMAGE_PREFIX=johndoe/ai-scene
  ```

#### 数据库配置 (Backend & Engine)
```bash
# 你的 PostgreSQL 连接 URL
SPRING_DATASOURCE_URL=jdbc:postgresql://<HOST>:<PORT>/<DB_NAME>
SPRING_DATASOURCE_USERNAME=<DB_USER>
SPRING_DATASOURCE_PASSWORD=<DB_PASSWORD>

# Engine 使用的 DSN (Python 格式)
# 格式: postgresql://<user>:<password>@<host>:<port>/<dbname>
# 注意: 如果密码包含特殊字符，必须进行 URL 编码
DB_DSN=postgresql://<DB_USER>:<DB_PASSWORD>@<HOST>:<PORT>/<DB_NAME>
```

**Redis 配置**
```bash
# Spring Boot 格式 (如果是简单 URL)
SPRING_REDIS_URL=redis://default:<PASSWORD>@<HOST>:<PORT>/0
```

**对象存储 (S3/Cloudflare R2)**
```bash
S3_STORAGE_REGION=auto
S3_STORAGE_ENDPOINT=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
S3_STORAGE_ACCESS_KEY=<ACCESS_KEY>
S3_STORAGE_SECRET_KEY=<SECRET_KEY>
S3_STORAGE_BUCKET=ai-scene-assets
# 公开访问的基础 URL
S3_STORAGE_PUBLIC_URL=https://<PUB_DOMAIN>
```

**AI 模型服务**
```bash
DASHSCOPE_API_KEY=<YOUR_ALIYUN_API_KEY>
```

## 3. 部署与验证

### 3.1 启动部署

1. 确保 GitHub Actions 已经成功构建并推送镜像。
2. 在 Coolify 中点击 **"Deploy"** 按钮。
3. Coolify 将从 GHCR 拉取预构建的镜像（**不会在服务器上构建**）。
4. 等待 2-3 分钟，部署完成。

### 3.2 验证部署

#### 方法 1：健康检查

```bash
# 检查 Backend 健康状态
curl https://your-backend-domain.com/health

# 预期输出：{"status":"UP"}
```

#### 方法 2：集成测试脚本

部署完成后，你可以在本地使用提供的 `integration_test.py` 脚本来验证服务是否正常。

```bash
# (可选) 如果你想在本地先构建镜像验证
./build.sh

# 安装依赖
pip install requests

# 运行测试 (替换为你的 Coolify 部署域名)
python integration_test.py https://your-backend-domain.com
```

---

## 4. 更新部署（自动化）

### 4.1 自动部署流程（推荐）

**只需推送代码，其余全自动！**

```bash
# 修改代码后提交
git add .
git commit -m "feat: new feature"
git push origin main

# 等待 5-10 分钟，以下步骤自动完成：
# 1. GitHub Actions 构建镜像并推送到 GHCR
# 2. 自动触发 Coolify Webhook
# 3. Coolify 拉取最新镜像（pull_policy: always）
# 4. 重启所有服务
# 5. 新版本自动上线 ✅
```

**查看部署进度**：
- GitHub Actions: `https://github.com/<username>/<repo>/actions`
- Coolify Logs: 在 Coolify 控制台查看实时日志

### 4.2 手动部署（备选方案）

如果自动部署失败，可以手动触发：

#### 方法 A：在 Coolify 手动重新部署

1. **推送代码**到 GitHub：
   ```bash
   git add .
   git commit -m "feat: new feature"
   git push origin main
   ```

2. **等待 GitHub Actions** 自动构建新镜像（约 5-10 分钟）。

3. **在 Coolify 中手动更新**：
   - 进入 Coolify 控制台
   - 点击项目的 **"Redeploy"** 按钮
   - Coolify 会因为 `pull_policy: always` 自动拉取最新的 `latest` 镜像

#### 方法 B：使用 Coolify CLI

```bash
# 通过 curl 手动触发 Webhook
curl -X POST "https://your-coolify.com/api/v1/deploy/webhooks/xxxxxxxx"
```

### 4.3 版本管理最佳实践

#### 使用语义化版本标签

```bash
# 创建版本标签
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin v1.2.0

# GitHub Actions 会自动构建多个标签：
# - ghcr.io/user/ai-scene-backend:v1.2.0
# - ghcr.io/user/ai-scene-backend:v1.2
# - ghcr.io/user/ai-scene-backend:latest
```

#### Coolify 环境变量配置

```bash
# 生产环境：使用稳定版本
IMAGE_TAG=v1.2.0

# 测试环境：使用最新开发版本
IMAGE_TAG=develop

# 快速迭代：使用 latest
IMAGE_TAG=latest
```

---

## 5. 故障排查

### 5.1 镜像拉取失败

**症状**：Coolify 报错 "Failed to pull image"

**解决方案**：

1. **检查镜像是否存在**：
   ```bash
   # 登录 GHCR
   echo $GITHUB_TOKEN | docker login ghcr.io -u <username> --password-stdin
   
   # 尝试拉取镜像
   docker pull ghcr.io/<username>/ai-scene-backend:latest
   ```

2. **检查镜像可见性**：
   - 进入 GitHub 仓库 → **Packages**
   - 找到对应的包 → **Package settings**
   - 确保 **Visibility** 设置为 **Public**（或在 Coolify 配置 GHCR 凭据）

3. **配置 Coolify 私有镜像访问**（如果使用私有仓库）：
   - 在 Coolify 中添加 Registry Credentials
   - Username: 你的 GitHub 用户名
   - Password: GitHub Personal Access Token (PAT)

### 5.2 GitHub Actions 构建失败

**症状**：Workflow 运行失败

**排查步骤**：

1. **检查 Secrets 配置**：
   - 进入 **Settings → Secrets and variables → Actions**
   - 确保 `VITE_API_BASE_URL` 和 `VITE_API_KEY` 已配置

2. **查看构建日志**：
   - 进入 **Actions** 选项卡
   - 点击失败的 Workflow 运行
   - 查看详细错误信息

3. **常见错误**：
   - **"denied: permission_denied"**: GHCR 权限不足，检查 `GITHUB_TOKEN` 权限
   - **"failed to solve: Dockerfile not found"**: 检查 Dockerfile 路径
   - **"Maven build failed"**: 检查 Java 代码编译错误

### 5.3 容器启动失败

**症状**：容器不断重启

**排查步骤**：

1. **查看 Coolify 日志**：
   - 点击服务 → **Logs** 选项卡
   - 查找启动错误信息

2. **常见问题**：
   - **数据库连接失败**：检查 `SPRING_DATASOURCE_URL` 配置
   - **Redis 连接失败**：检查 `SPRING_REDIS_URL` 配置
   - **S3 配置错误**：检查 `S3_STORAGE_*` 环境变量

---

## 6. 进阶配置

### 6.1 使用 Docker Hub 代替 GHCR

如果你想使用 Docker Hub：

1. **修改 GitHub Actions workflow**：
   ```yaml
   env:
     REGISTRY: docker.io
     IMAGE_PREFIX: your-dockerhub-username/ai-scene
   ```

2. **配置 Docker Hub Secrets**：
   - `DOCKERHUB_USERNAME`
   - `DOCKERHUB_TOKEN`

3. **更新 Coolify 环境变量**：
   ```bash
   DOCKER_REGISTRY=docker.io
   DOCKER_IMAGE_PREFIX=your-dockerhub-username/ai-scene
   ```

### 6.2 多环境部署

#### 为不同环境使用不同分支/标签

| 环境 | Git 分支 | 镜像标签 | Coolify `IMAGE_TAG` |
|------|---------|----------|--------------------|
| 开发 | develop | develop | `develop` |
| 测试 | main | main | `main` |
| 生产 | v*.*.* | v1.2.0 | `v1.2.0` |

#### 在 Coolify 创建多个实例

1. 为每个环境创建独立的 Coolify 项目
2. 使用不同的 `IMAGE_TAG` 环境变量
3. 配置不同的数据库/Redis 连接

---

## 7. 参考资料

- [GitHub Container Registry 文档](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [GitHub Actions Docker Build 文档](https://docs.docker.com/build/ci/github-actions/)
- [Coolify 官方文档](https://coolify.io/docs)

---

## 附录：旧版本源码部署方式

如果你仍然需要在 Coolify 上直接构建镜像，可以参考以下配置：

### docker-compose.local-build.yaml （示例）

```yaml
services:
  ai-scene-backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    image: ai-scene-backend:latest
    # ... 其他配置
```

**注意**：这种方式会在服务器上执行 Maven 和 NPM 构建，需要 10-15 分钟且占用大量 CPU/内存。
