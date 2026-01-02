# Coolify 部署指南

本指南将帮助你将 `AI Scene to Video` 项目部署到 Coolify 平台。

## 1. 准备工作

确保你已经拥有：
1. Coolify 实例的访问权限。
2. 自部署的 PostgreSQL 数据库连接信息。
3. 自部署的 Redis 连接信息。
4. Supabase (或兼容 S3) 的存储桶信息。
5. 阿里云 DashScope API Key (用于 Qwen-VL 和 Qwen-Plus)。

## 2. 项目配置

### 2.1 推送代码到 Git 仓库
由于我们的部署依赖源码构建（`build: context`），你需要先将包含 `docker-compose.coolify.yml` 的最新代码推送到 GitHub 或 GitLab 等远程仓库。

### 2.2 在 Coolify 创建资源
1. 在 Coolify 面板中，点击 **"New Resource"**。
2. 选择 **"Git Based"** 下的 **"Private Repository (with GitHub App)"** (如果是私有仓库) 或 **"Public Repository"**。
3. 选择你的代码仓库。
4. **关键步骤**: 
   - 在配置页面，Coolify 可能会尝试自动检测。
   - 找到 **"Docker Compose Location"** (或类似配置项)，将其改为 `/docker-compose.coolify.yml`。
   - 确保 **Build Pack** 选为 **Docker Compose**。

**注意**: 本配置定义了三个服务：
- `ai-scene-backend`: Java 后端服务
- `ai-scene-engine`: Python AI 引擎服务
- `ai-scene-frontend`: Vue 前端服务 (Nginx)

Coolify 会自动根据配置中的 `build` 指令构建镜像。`ai-scene-backend` 使用多阶段构建，会自动在构建过程中编译 Java 代码，**无需手动上传 JAR 包**。
前端服务 `ai-scene-frontend` 会映射容器内的 80 端口到宿主机的 3000 端口（可根据需要在 Coolify 中调整）。

### 2.3 配置环境变量 (Environment Variables)

你需要在 Coolify 的 "Environment Variables" 区域添加以下变量。请将值替换为你的实际配置。

**数据库配置 (Backend & Engine)**
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

1. 点击 **Deploy** 按钮开始部署。
2. 等待 Build 和 Deploy 完成。Coolify 会分别构建 Backend 和 Engine 镜像。
3. 部署成功后，获取 `ai-scene-backend` 服务的公开域名（如果在 Coolify 配置了域名）。

## 4. 运行测试脚本

部署完成后，你可以在本地使用提供的 `integration_test.py` 脚本来验证服务是否正常。

```bash
# (可选) 如果你想在本地先构建镜像验证
./build.sh

# 安装依赖
pip install requests

# 运行测试 (替换为你的 Coolify 部署域名)
python integration_test.py https://your-backend-domain.com
```

### 注意事项
- 测试脚本会上传一个虚假的视频文件。如果想测试真实的 AI 识别能力，请修改脚本中的 `dummy_filename` 为真实的 MP4 文件路径。
- 如果部署失败，请查看 Coolify 的 "Logs" 选项卡，检查 Backend 或 Engine 的启动日志。
