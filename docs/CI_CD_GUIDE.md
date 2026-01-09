# CI/CD 部署指南

## 概述

本项目采用 **GitHub Actions** 进行自动化构建和镜像推送，配合 **Coolify** 进行容器编排和部署。这种方式将构建压力从生产服务器转移到 GitHub 的 CI/CD 环境，显著提升部署效率。

---

## 架构对比

### 旧方式：源码部署（Source-based Deployment）

```
┌─────────────┐      ┌──────────────┐
│   Git Push  │─────>│   Coolify    │
└─────────────┘      │   Server     │
                     │              │
                     │ 1. Git Clone │
                     │ 2. Maven     │ ⚠️ CPU/内存消耗大
                     │ 3. NPM       │
                     │ 4. Docker    │
                     │    Build     │
                     │ 5. Run       │
                     └──────────────┘
                     ⏱️ 10-15 分钟
```

### 新方式：镜像部署（Image-based Deployment）

```
┌─────────────┐      ┌──────────────┐      ┌──────────────┐
│   Git Push  │─────>│   GitHub     │─────>│   GitHub     │
└─────────────┘      │   Actions    │      │   Container  │
                     │              │      │   Registry   │
                     │ 1. Maven     │      │   (GHCR)     │
                     │ 2. NPM       │      │              │
                     │ 3. Docker    │      └──────┬───────┘
                     │    Build     │             │
                     │ 4. Push      │             │
                     └──────────────┘             │
                     ⏱️ 5-10 分钟                 │
                                                   ▼
                                          ┌──────────────┐
                                          │   Coolify    │
                                          │   Server     │
                                          │              │
                                          │ 1. Pull      │ ✅ 轻量级
                                          │ 2. Run       │
                                          └──────────────┘
                                          ⏱️ 2-3 分钟
```

---

## 配置步骤

### 1. 启用 GitHub Actions

#### 1.1 配置 Repository Secrets

在 GitHub 仓库中添加以下 Secrets：

**路径**: `Settings → Secrets and variables → Actions → New repository secret`

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `VITE_API_BASE_URL` | 前端 API 地址 | `https://api.example.com` |
| `VITE_API_KEY` | 前端 API 密钥 | `sk-xxx` |

**注意**:
- `GITHUB_TOKEN` 无需手动配置，GitHub 会自动注入
- `GITHUB_TOKEN` 自动拥有 `write:packages` 权限

#### 1.2 设置包可见性

构建完成后，镜像会推送到 GitHub Container Registry (GHCR)。默认为私有，需要调整：

1. 进入 GitHub 仓库 → **Packages** 标签
2. 找到 `ai-scene-backend`, `ai-scene-engine`, `ai-scene-frontend`
3. 点击进入包设置 → **Package settings**
4. 修改 **Visibility** 为 **Public**（或在 Coolify 配置凭据访问私有镜像）

### 2. 配置 Coolify

#### 2.1 创建 Docker Compose 项目

1. 登录 Coolify 控制台
2. 点击 **New Resource** → 选择 **Docker Compose**
3. 选择 Git 仓库类型（Public/Private）
4. 填写仓库地址和分支
5. **Docker Compose Location**: `docker-compose.coolify.yaml`

#### 2.2 配置环境变量

在 Coolify 的 **Environment Variables** 区域添加：

```bash
# ===== 镜像配置（必填）=====
DOCKER_REGISTRY=ghcr.io
DOCKER_IMAGE_PREFIX=<your-github-username>/ai-scene
IMAGE_TAG=latest

# ===== 数据库配置 =====
SPRING_DATASOURCE_URL=jdbc:postgresql://host:5432/dbname
SPRING_DATASOURCE_USERNAME=postgres
SPRING_DATASOURCE_PASSWORD=yourpassword
DB_DSN=postgresql://user:pass@host:5432/dbname

# ===== Redis 配置 =====
SPRING_REDIS_URL=redis://host:6379/0

# ===== S3 存储配置 =====
S3_STORAGE_REGION=auto
S3_STORAGE_ENDPOINT=https://account.r2.cloudflarestorage.com
S3_STORAGE_ACCESS_KEY=xxx
S3_STORAGE_SECRET_KEY=xxx
S3_STORAGE_BUCKET=ai-scene-assets
S3_STORAGE_PUBLIC_URL=https://cdn.example.com

# ===== AI 服务配置 =====
DASHSCOPE_API_KEY=sk-xxx

# ===== BGM 配置（可选）=====
APP_BGM_AUTO_SELECT=true
```

**关键配置说明**:

- `DOCKER_IMAGE_PREFIX`: 必须与你的 GitHub 用户名匹配
  - 仓库: `https://github.com/johndoe/ai-scene-to-video`
  - 设置: `DOCKER_IMAGE_PREFIX=johndoe/ai-scene`

- `IMAGE_TAG`: 控制使用哪个版本的镜像
  - `latest` - 最新的 main 分支
  - `develop` - 开发分支
  - `v1.2.0` - 特定版本标签

---

## 工作流程

### 自动化构建流程

当你推送代码到 GitHub 时，会自动触发以下流程：

```mermaid
graph LR
    A[推送代码] --> B{触发条件}
    B -->|main 分支| C[GitHub Actions]
    B -->|develop 分支| C
    B -->|v* 标签| C
    C --> D[并行构建 3 个服务]
    D --> E1[Backend 镜像]
    D --> E2[Engine 镜像]
    D --> E3[Frontend 镜像]
    E1 --> F[推送到 GHCR]
    E2 --> F
    E3 --> F
    F --> G[Coolify 拉取新镜像]
    G --> H[重启容器]
```

### 手动部署流程

#### 方式 1：使用 latest 标签（快速迭代）

```bash
# 1. 推送代码
git add .
git commit -m "feat: new feature"
git push origin main

# 2. 等待 GitHub Actions 完成（5-10分钟）

# 3. 在 Coolify 中点击 "Redeploy"
```

#### 方式 2：使用语义化版本（生产环境）

```bash
# 1. 创建版本标签
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin v1.2.0

# 2. 等待 GitHub Actions 完成

# 3. 在 Coolify 中修改环境变量
IMAGE_TAG=v1.2.0

# 4. 点击 "Restart"
```

---

## 镜像标签策略

GitHub Actions 会自动为每次构建生成多个标签：

| 触发条件 | 生成的标签 |
|---------|-----------|
| 推送到 `main` | `latest`, `main`, `main-<short-sha>` |
| 推送到 `develop` | `develop`, `develop-<short-sha>` |
| 推送标签 `v1.2.3` | `v1.2.3`, `v1.2`, `v1`, `latest` |
| Pull Request | `pr-123` （不推送到仓库）|

**推荐使用场景**:

- **开发环境**: `IMAGE_TAG=develop`
- **测试环境**: `IMAGE_TAG=main`
- **生产环境**: `IMAGE_TAG=v1.2.0` (固定版本)

---

## 故障排查

### 问题 1: 镜像拉取失败

**错误日志**:
```
Error response from daemon: pull access denied for ghcr.io/user/ai-scene-backend
```

**解决方案**:

1. 检查包可见性是否为 Public
2. 如果是私有镜像，配置 Coolify Registry Credentials:
   - Registry: `ghcr.io`
   - Username: GitHub 用户名
   - Password: Personal Access Token (需要 `read:packages` 权限)

### 问题 2: GitHub Actions 构建失败

**常见错误**:

- **"denied: permission_denied"**
  - 原因: `GITHUB_TOKEN` 权限不足
  - 解决: 检查仓库 `Settings → Actions → General → Workflow permissions` 设置为 **Read and write permissions**

- **"failed to solve with frontend dockerfile.v0"**
  - 原因: Dockerfile 语法错误或构建参数缺失
  - 解决: 检查 `VITE_API_BASE_URL` 和 `VITE_API_KEY` Secrets 是否已配置

- **"Maven build failed"**
  - 原因: Java 代码编译错误
  - 解决: 本地运行 `mvn clean verify` 确保代码无误

### 问题 3: 容器启动后不断重启

**排查步骤**:

1. 在 Coolify 中查看日志: `服务 → Logs`
2. 检查环境变量是否完整
3. 验证依赖服务（DB/Redis/S3）连通性

**常见原因**:

```bash
# 数据库连接失败
SPRING_DATASOURCE_URL=jdbc:postgresql://wrong-host:5432/db

# Redis 连接失败
SPRING_REDIS_URL=redis://wrong-host:6379/0

# S3 认证失败
S3_STORAGE_ACCESS_KEY=invalid_key
```

---

## 高级配置

### 使用 Docker Hub 代替 GHCR

如果你想使用 Docker Hub:

**1. 修改 `.github/workflows/build-and-push.yml`**:

```yaml
env:
  REGISTRY: docker.io
  IMAGE_PREFIX: your-dockerhub-username/ai-scene
```

**2. 添加 Docker Hub Secrets**:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

**3. 更新 workflow 登录步骤**:

```yaml
- name: Log in to Docker Hub
  uses: docker/login-action@v3
  with:
    username: ${{ secrets.DOCKERHUB_USERNAME }}
    password: ${{ secrets.DOCKERHUB_TOKEN }}
```

**4. 更新 Coolify 环境变量**:

```bash
DOCKER_REGISTRY=docker.io
DOCKER_IMAGE_PREFIX=your-dockerhub-username/ai-scene
```

### 多环境部署策略

| 环境 | Git 分支/标签 | IMAGE_TAG | 数据库 |
|------|--------------|-----------|--------|
| 开发 | `develop` | `develop` | dev-db |
| 测试 | `main` | `main` | test-db |
| 预生产 | `v1.2.0-rc.1` | `v1.2.0-rc.1` | staging-db |
| 生产 | `v1.2.0` | `v1.2.0` | prod-db |

**在 Coolify 中创建 4 个独立项目，每个使用不同的**:
- `IMAGE_TAG` 环境变量
- 数据库连接配置
- Redis 实例

---

## 性能对比

| 指标 | 源码部署 | 镜像部署 |
|------|---------|---------|
| 服务器 CPU 峰值 | 90-100% | 10-20% |
| 服务器内存占用 | 4-6 GB | 1-2 GB |
| 部署时间 | 10-15 分钟 | 2-3 分钟 |
| 网络带宽消耗 | 500 MB (源码) | 1.5 GB (镜像) |
| 失败后重试成本 | 高 | 低 |
| 可回滚性 | 差 | 优秀 |

**结论**: 镜像部署更适合生产环境，构建时间更稳定，服务器资源占用更少。

---

## 参考资料

- [GitHub Actions 官方文档](https://docs.github.com/en/actions)
- [GitHub Container Registry 指南](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [Coolify 官方文档](https://coolify.io/docs)

---

## 常见问题

**Q: 如何回滚到上一个版本？**

A: 修改 Coolify 的 `IMAGE_TAG` 环境变量为旧版本号，然后点击 Restart。

**Q: 可以在本地构建并推送镜像吗？**

A: 可以，但不推荐。应该统一使用 GitHub Actions 确保构建环境一致。

**Q: 如何查看镜像大小？**

A: 访问 `https://github.com/<username>/<repo>/pkgs/container/<image-name>` 查看详情。

**Q: 如何清理旧镜像？**

A: 在 GitHub Package 页面手动删除，或配置 GitHub Actions 自动清理策略。

**Q: 前端环境变量如何更新？**

A: 前端环境变量在构建时被烘焙到镜像中，需要重新构建镜像。更新 GitHub Secrets 后推送新代码即可。
