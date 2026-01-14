---
trigger: always_on
---
# 项目规则（ai-scene-to-video）

本规则用于约束本仓库的开发/改动方式，避免引入与当前工程形态冲突的实现。

> **最后更新**: 2026-01-08  
> **版本**: v2.0 - 整合架构、鉴权、可观测性规则

## 1. 仓库结构与职责边界

- `backend/`：Java 17 + Spring Boot 3（业务编排、状态机、DB/Redis/S3 访问、对外 HTTP API）
- `engine/`：Python 3.10 + Celery（耗时任务：视觉分析、脚本/音频生成、渲染合成）
- `frontend/`：Vue 3 + TypeScript + Vite + Vant（H5 前端）
- `.qoder/rules/`：仓库开发规则（本文件 + java_code_style.md + python_code_style.md）

原则：
- `backend` 必须无状态，状态下沉到 Postgres/Redis/S3。
- `engine` 只做 CPU/GPU/FFmpeg/AI 等重任务，不直接承载对外流量（目前以 Celery Worker 形式运行）。

## 1.1 代码规范引用

本项目遵循业界标准的代码规范：

### Backend (Java)
- **主要规范**: [阿里巴巴Java开发手册](https://alibaba.github.io/p3c/) + [Google Java Style Guide](https://google.github.io/styleguide/javaguide.html)
- **详细规范**: 参见 [.qoder/rules/java_code_style.md](java_code_style.md)
- **关键要求**:
  - 类名使用 UpperCamelCase，方法名使用 lowerCamelCase
  - 缩进使用 4 个空格，禁止使用 Tab
  - 单行代码不超过 120 字符
  - 所有公共方法必须有 Javadoc 注释
  - 单元测试覆盖率 ≥ 80%（JaCoCo 强制）

### Engine (Python)
- **主要规范**: [PEP 8 - Style Guide for Python Code](https://peps.python.org/pep-0008/)
- **详细规范**: 参见 [.qoder/rules/python_code_style.md](python_code_style.md)
- **关键要求**:
  - 函数名、变量名使用 snake_case，类名使用 CapWords
  - 缩进使用 4 个空格
  - 单行代码不超过 88 字符（Black 默认）
  - 所有公共函数必须有文档字符串
  - 使用 Black 进行代码格式化

### Frontend (TypeScript/Vue)
- **主要规范**: TypeScript 严格模式 + Vue 3 官方风格指南
- **关键要求**:
  - 使用 2 个空格缩进
  - 使用 vue-tsc 进行类型检查
  - 组件名使用 PascalCase

## 2. 本地开发与常用命令

### 2.1 Docker Compose（推荐的一键方式）

在仓库根目录：

```bash
docker compose -f docker-compose.coolify.yaml up --build
```

说明：
- **部署平台**: 本项目使用 **Coolify** 进行部署和管理。
- **环境变量注入**: 所有配置必须通过 Coolify 的环境变量功能注入，Compose 文件会自动透传这些变量。
- **配置规范**:
  - ✅ 在 Coolify 控制台配置环境变量（Environment Variables）
  - ✅ 使用 `${VARIABLE_NAME}` 在 compose 文件中引用
  - ❌ 禁止在 compose 文件中硬编码任何密钥或配置值
  - ❌ 禁止使用 `.env` 文件（Coolify 环境下不生效）
- **本地开发**: 需要先准备对应依赖服务（DB/Redis/S3），并通过环境变量或 `.env` 文件提供配置。

### 2.2 Backend（Spring Boot）

在仓库根目录：

```bash
mvn -f backend/pom.xml spring-boot:run
```

测试/质量门禁：

```bash
mvn -f backend/pom.xml test
mvn -f backend/pom.xml verify
```

说明：
- `verify` 会触发 JaCoCo 覆盖率校验（当前阈值：指令覆盖率 ≥ 0.80），低于阈值会失败。

### 2.3 Engine（Celery Worker）

在仓库根目录（本地 Python 运行）：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r engine/requirements.txt
cd engine
celery -A worker.celery_app worker --loglevel=info
```

说明：
- `engine/Dockerfile` 的默认启动命令为 `celery -A worker.celery_app worker --loglevel=info`（容器内工作目录为 `/app`）。

### 2.4 Frontend（Vue）

在仓库根目录：

```bash
npm --prefix frontend ci
npm --prefix frontend run dev
```

构建：

```bash
npm --prefix frontend run build
```

类型检查（本仓库当前未配置 ESLint；以 TS 严格模式 + vue-tsc 为主）：

```bash
cd frontend
npx vue-tsc --noEmit -p tsconfig.app.json
```

## 3. 关键运行参数（环境变量）

根目录提供 `.env.example` 作为模板，主要变量：
- Backend：
  - `SPRING_DATASOURCE_URL / SPRING_DATASOURCE_USERNAME / SPRING_DATASOURCE_PASSWORD`
  - `SPRING_REDIS_URL`
  - `S3_STORAGE_REGION / S3_STORAGE_ENDPOINT / S3_STORAGE_ACCESS_KEY / S3_STORAGE_SECRET_KEY / S3_STORAGE_BUCKET / S3_STORAGE_PUBLIC_URL`
- Engine：
  - `REDIS_URL`（通常复用 `SPRING_REDIS_URL`）
  - `DB_DSN`（Python DSN 格式）
  - `DASHSCOPE_API_KEY`
- Frontend：
  - `VITE_API_BASE_URL`
  - `VITE_API_KEY`（会以 `Authorization: ApiKey <key>` 形式注入请求头）

注意：
- 禁止在代码库提交任何真实密钥/Token/密码，只能通过环境变量注入。

## 4. API 与鉴权约束

- 健康检查白名单：
  - `GET /health`：仅进程存活检查
  - `GET /ready`：依赖就绪检查（当前实现包含 DB 连接校验）
- 项目 API 前缀：
  - `backend` 控制器当前使用 `/v1/projects`（见 `ProjectController`）
- 鉴权与信任模型以 `.trae/rules/dev_rules_auth.md` 为准：
  - 业务服务默认不信任请求；仅信任由网关注入的 `X-User-Id / X-User-Role` 等头
  - 所有接口默认需要鉴权，除显式白名单外禁止“偷偷放开”

## 5. 可观测性与日志

- 必须读取并透传 `X-Request-Id`；响应必须回写 `X-Request-Id`（后端已通过 `RequestLoggingFilter` 实现）。
- 生产环境必须输出 JSON 日志；字段规范以 `.trae/rules/dev_rules_ops.md` 为准。
- 禁止打印任何敏感信息（密码、密钥、用户 Token、Presigned URL 的敏感参数）。

## 6. 数据与迁移规范

- 禁止在业务代码执行 DDL；所有 Schema 变更必须走 Flyway（`backend/src/main/resources/db/migration`）。
- Redis 键必须包含前缀 `ai-video:` 以避免跨服务冲突（见 `.trae/rules/dev_rules_infra.md`）。
- Presigned URL 有效期不得超过 1 小时（见 `.trae/rules/dev_rules_auth.md`）。

## 7. 端到端验证

仓库根目录提供 `integration_test.py` 用于冒烟验证后端：

```bash
pip install requests
python integration_test.py http://localhost:8090
```

---

## 8. 架构与基础设施规范

### 8.1 架构原则

- **微服务/单体边界**: 后端采用 Monolithic 架构 (`backend`)，但通过 Python Worker (`engine`) 剥离 CPU/GPU 密集型任务。
- **无状态设计**: 业务服务必须无状态，所有状态下沉至 DB/Redis/S3。
- **环境隔离**: 严禁将生产环境凭据提交至代码库，必须通过环境变量注入。

### 8.2 统一依赖

#### 数据库 (PostgreSQL)
- 必须复用自部署的统一 PostgreSQL JDBC 连接。
- **禁止在业务代码中执行 DDL**，必须使用 Flyway 管理 Schema 变更（迁移文件位于 `backend/src/main/resources/db/migration`）。
- 迁移文件命名规范：`V{version}__{description}.sql`（如 `V6__add_description_to_projects.sql`）。

#### 对象存储 (Object Storage)
- 必须复用 Supabase Storage (S3 兼容) 或 Cloudflare R2。
- 上传大文件（>10MB）必须使用 Presigned URL 或流式上传。
- **Presigned URL 有效期不得超过 1 小时**。

#### 缓存与消息 (Redis)
- 必须复用自部署的统一 Redis。
- **键名必须包含前缀 `ai-video:`** 以防冲突（如 `ai-video:project:{id}:status`）。
- Celery 队列名称：`ai-video:celery`（见 `application.yml`）。

### 8.3 网络与暴露

- **公网入口**: 仅 Nginx 网关可暴露 80/443。
- **内部通信**: 服务间调用必须走内网 DNS (Docker Service Name)，禁止公网回绕。
- **容器端口**:
  - Backend: 8090
  - Frontend: 80 (Nginx)
  - Engine: 无对外端口（仅 Celery Worker）

---

## 9. 鉴权与安全规范

### 9.1 鉴权模型 (Authentication)

- **零信任原则**: 业务服务 (`backend`) 默认不信任任何请求，除非包含合法的网关头。
- **信任源头**: 仅信任以下 HTTP Header（由网关校验并注入）：
  - `X-User-Id`: 经过验证的用户 ID
  - `X-User-Role`: 用户的 RBAC 角色
  - `X-Internal-Auth`: 服务间调用的共享密钥（用于 Worker 回调）

### 9.2 授权规范 (Authorization)

- **Scope 命名规范**: `<app>.<resource>.<action>`
  - ✅ 正例: `ai-video.project.create`
  - ❌ 反例: `create_project`
- **默认拒绝**: 所有 API 接口默认需要鉴权，除了显式白名单。
- **鉴权白名单**:
  - `GET /health` - 进程存活检查
  - `GET /ready` - 依赖就绪检查
  - `/.well-known/*` - 标准发现端点

### 9.3 数据安全

- **敏感字段**: 用户的手机号、邮箱等 PII 信息在落库前必须脱敏或加密。
- **密钥管理**: 禁止在日志中打印任何密码、API Key、Token、Presigned URL 的敏感参数。
- **环境变量**: 所有密钥必须通过环境变量注入，禁止硬编码。

---

## 10. 可观测性与运维规范

### 10.1 全链路追踪 (Distributed Tracing)

#### Request ID 处理规范

1. **接收**: 所有 HTTP 接口必须读取 `X-Request-Id` 请求头
2. **透传**: 调用下游服务（Worker、外部 API）时必须携带此 ID
3. **响应**: HTTP Response Header 必须回写 `X-Request-Id`
4. **日志关联**: 所有日志必须包含 `request_id` 字段

**实现要点**:
- Backend: 已通过 `RequestLoggingFilter` 实现（见 `backend/src/main/java/com/aiscene/config/RequestLoggingFilter.java`）
- Engine: 通过 Celery 的 `task_prerun` signal 注入（见 `engine/worker.py`）

### 10.2 健康检查端点

#### `/health` - 进程存活检查
- **用途**: Kubernetes liveness probe
- **逻辑**: 仅检查进程是否存活
- **响应**: `200 OK` (无 Body 或简单 JSON)

#### `/ready` - 依赖就绪检查
- **用途**: Kubernetes readiness probe
- **逻辑**: 检查 DB、Redis、S3 连接池是否可用
- **响应**: 
  - `200 OK` - 所有依赖可用
  - `503 Service Unavailable` - 任一依赖不可用

### 10.3 日志规范

#### 格式要求
- **开发环境**: 可读文本格式
- **生产环境**: 必须输出 JSON 格式日志

#### 必填字段
```json
{
  "timestamp": "2026-01-08T21:35:47.123Z",  // ISO-8601
  "level": "INFO",                          // INFO/WARN/ERROR
  "service": "ai-scene-backend",            // 服务名称
  "trace_id": "req-abc123",                 // 即 request_id
  "user_id": "user-123",                    // 用户 ID（如有）
  "message": "Project created successfully",
  "event": "project.created",               // 事件类型（结构化日志）
  "project_id": "proj-456"                  // 业务上下文
}
```

#### 日志级别使用规范
- **ERROR**: 需要人工介入的异常（如第三方 API 失败、数据库连接断开）
- **WARN**: 可自动恢复的异常（如重试成功、降级使用默认值）
- **INFO**: 关键业务事件（如用户创建项目、视频渲染完成）
- **DEBUG**: 调试信息（生产环境禁用）

#### 禁止事项
- ❌ 禁止打印密码、API Key、Token
- ❌ 禁止打印完整的 Presigned URL（可打印不含签名参数的部分）
- ❌ 禁止打印用户敏感信息（手机号、身份证号等）

### 10.4 配置验证机制

#### Engine 配置验证
- **触发时机**: Worker 启动时自动执行（见 `engine/worker.py`）
- **验证内容**:
  - ✅ `DASHSCOPE_API_KEY` 已设置
  - ✅ `DB_DSN` 格式正确
  - ✅ S3 存储配置完整
  - ✅ 功能依赖项检查（如 SFX 路径存在）
- **失败处理**: 仅记录警告日志，不阻断启动

**示例输出**:
```
[WARN] Config validation: SFX_ENABLED but library path not found: /app/sfx_library
[WARN] Config validation: VISUAL_ENHANCEMENT_ENABLED but DASHSCOPE_API_KEY missing
```

### 10.5 变更管理 (GitOps)

#### 数据库变更
1. 创建 Flyway 迁移文件（`V{n}__description.sql`）
2. 本地测试迁移：`mvn -f backend/pom.xml flyway:migrate`
3. 提交 PR，触发 CI 验证
4. 合并后自动部署到测试环境

#### 配置变更
1. 修改 `.env.example` 添加新配置项
2. 更新相关文档（`README.md` 或本规则文件）
3. 通知运维团队更新生产环境变量

#### 鉴权变更
- 修改路由配置或权限范围必须提交 PR
- **验收标准**: 必须提供测试环境的 `X-Request-Id` 以证明变更有效且无副作用

---

## 11. 质量门禁

### 11.1 Backend (Java)

```bash
# 单元测试
mvn -f backend/pom.xml test

# 质量门禁（包含代码覆盖率检查）
mvn -f backend/pom.xml verify
```

**覆盖率要求**:
- 指令覆盖率 (Instruction Coverage): ≥ 80%
- 分支覆盖率 (Branch Coverage): ≥ 70%

### 11.2 Frontend (Vue)

```bash
# 类型检查
cd frontend
npx vue-tsc --noEmit -p tsconfig.app.json

# 构建验证
npm run build
```

### 11.3 Engine (Python)

```bash
# 代码格式检查
cd engine
python -m black --check .
python -m flake8 .

# 类型检查
python -m mypy .
```

---

## 12. 故障排查指南

### 12.1 常见问题

#### 问题：视频渲染失败
1. 检查 Engine Worker 日志：`docker logs ai-scene-engine`
2. 查找 `event: video.clip.open_failed` 或 `event: render.failed`
3. 验证 S3 存储可访问性
4. 检查 FFmpeg 版本（需要 ≥ 4.0）

#### 问题：AI 增强不生效
1. 确认 `VISUAL_ENHANCEMENT_ENABLED=true`
2. 验证 `DASHSCOPE_API_KEY` 有效
3. 检查日志中是否有 `event: ai_enhancement.failed`

#### 问题：配置验证失败
1. 启动时查看警告日志
2. 对照 `.env.example` 补全缺失配置
3. 使用 `Config.validate()` 方法手动验证

### 12.2 日志查询示例

```bash
# 查询特定 Request ID 的所有日志
docker logs ai-scene-backend | grep "req-abc123"

# 查询视频渲染事件
docker logs ai-scene-engine | grep '"event":"render'

# 查询错误日志
docker logs ai-scene-backend | grep '"level":"ERROR"'
```

---

## 附录：快速参考

### A. 环境变量速查表

| 变量名 | 服务 | 必填 | 说明 |
|--------|------|------|------|
| `SPRING_DATASOURCE_URL` | Backend | ✅ | PostgreSQL JDBC URL |
| `DASHSCOPE_API_KEY` | Engine | ✅ | 阿里云通义千问 API Key |
| `S3_STORAGE_ENDPOINT` | Both | ✅ | S3 兼容存储端点 |
| `SUBTITLE_ENABLED` | Engine | ❌ | 字幕功能开关（默认 true）|
| `VISUAL_ENHANCEMENT_ENABLED` | Engine | ❌ | AI 视觉增强开关（默认 false）|
| `RENDER_THREADS` | Engine | ❌ | 渲染线程数（默认 4）|

### B. 关键文件路径

- **配置**: `.env` (本地), `application.yml` (Backend), `config.py` (Engine)
- **迁移**: `backend/src/main/resources/db/migration/`
- **日志配置**: `backend/src/main/resources/logback-spring.xml`
- **路由定义**: `backend/src/main/java/com/aiscene/controller/`
- **任务定义**: `engine/tasks.py`

### C. 有用的命令

```bash
# 完整构建与启动
docker compose -f docker-compose.coolify.yaml up --build

# 单独重启 Engine
docker compose restart engine

# 查看实时日志
docker compose logs -f backend engine

# 数据库迁移状态
mvn -f backend/pom.xml flyway:info

# 端到端测试
python integration_test.py http://localhost:8090
```

---

## 13. Coolify 部署规范

### 13.1 部署平台约束

**项目使用 Coolify 作为开箱即用的 PaaS 部署平台。**

#### 基本原则
- ✅ **唯一配置源**: Coolify 控制台的 Environment Variables
- ✅ **Compose 透传**: `docker-compose.coolify.yaml` 通过 `${VAR}` 语法引用环境变量
- ❌ **禁止 .env 文件**: Coolify 环境下 `.env` 文件不会被自动加载
- ❌ **禁止硬编码**: 任何密钥、地址、端口均不能写在代码或 Compose 文件中

### 13.2 环境变量透传机制

#### Coolify 配置流程

1. **在 Coolify 控制台添加环境变量**
   ```
   路径: Project > Environment > Environment Variables
   ```

2. **变量转换规则**
   - Coolify 会将所有配置的环境变量注入到容器运行时
   - Compose 文件中的 `${VARIABLE_NAME}` 会自动替换

3. **示例：Compose 文件中的引用**
   ```yaml
   # docker-compose.coolify.yaml
   services:
     backend:
       environment:
         - SPRING_DATASOURCE_URL=${SPRING_DATASOURCE_URL}
         - SPRING_DATASOURCE_USERNAME=${SPRING_DATASOURCE_USERNAME}
         - SPRING_DATASOURCE_PASSWORD=${SPRING_DATASOURCE_PASSWORD}
         - S3_STORAGE_ENDPOINT=${S3_STORAGE_ENDPOINT}
   
     engine:
       environment:
         - REDIS_URL=${REDIS_URL}
         - DB_DSN=${DB_DSN}
         - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
         - SUBTITLE_ENABLED=${SUBTITLE_ENABLED:-true}
   ```

4. **默认值语法**
   - 支持 `${VAR:-default}` 语法
   - 例：`${SUBTITLE_ENABLED:-true}` 表示如果未配置则默认为 `true`

### 13.3 必须配置的环境变量

#### Engine 核心配置
```bash
# 数据库 DSN（必填）
DB_DSN=postgresql://postgres:password@postgres-host:5432/ai_scene

# Redis（必填）
REDIS_URL=redis://redis-host:6379/0

# AI 服务（必填）
DASHSCOPE_API_KEY=sk-your-dashscope-key

# Celery 队列名称
CELERY_QUEUE_NAME=ai-video:celery
```

#### Backend 核心配置
```bash
# 数据库连接（必填）
SPRING_DATASOURCE_URL=jdbc:postgresql://postgres-host:5432/ai_scene
SPRING_DATASOURCE_USERNAME=postgres
SPRING_DATASOURCE_PASSWORD=your_secure_password

# Redis 连接（必填）
SPRING_REDIS_URL=redis://redis-host:6379/0

# S3 存储（必填）
S3_STORAGE_REGION=auto
S3_STORAGE_ENDPOINT=https://your-account.r2.cloudflarestorage.com
S3_STORAGE_ACCESS_KEY=your_access_key
S3_STORAGE_SECRET_KEY=your_secret_key
S3_STORAGE_BUCKET=ai-scene-assets
S3_STORAGE_PUBLIC_URL=https://your-cdn.com

# 内置 BGM 配置（可选）
APP_BGM_AUTO_SELECT=true  # 创建项目时自动随机选择 BGM
# BGM URLs 在 application.yml 中配置
```

#### “温情生活风”增强功能（可选）
```bash
# 字幕配置
SUBTITLE_ENABLED=true
SUBTITLE_STYLE=elegant

# AI 视觉增强
VISUAL_ENHANCEMENT_ENABLED=false
VISUAL_ENHANCEMENT_STRATEGY=smart

# 音频增强
AUTO_DUCKING_ENABLED=false
BGM_VOLUME=0.15

# 性能优化
RENDER_THREADS=4
MAX_VIDEO_RESOLUTION=1080
```

### 13.4 Coolify 部署流程

#### 首次部署

1. **在 Coolify 创建项目**
   - 选择 Docker Compose 类型
   - 指向 Git 仓库
   - 选择 `docker-compose.coolify.yaml`

2. **配置环境变量**
   - 按照上述必填配置逐一填写
   - 注意保密变量勾选 "Secret" 选项

3. **验证配置**
   - 点击 "Deploy" 前先检查环境变量完整性
   - 可使用 "Preview Environment Variables" 预览

4. **启动部署**
   ```
   Coolify 会自动：
   1. 拉取代码
   2. 注入环境变量
   3. 执行 docker compose up
   4. 配置反向代理
   ```

#### 更新部署

**代码更新**:
- Git push 后自动触发（如果配置了 Webhook）
- 或在 Coolify 控制台手动点击 "Redeploy"

**环境变量更新**:
1. 在 Coolify 控制台修改变量
2. 点击 "Restart" 使配置生效
3. 无需重新构建镜像

### 13.5 本地开发与 Coolify 环境差异

| 项目 | 本地开发 | Coolify 部署 |
|------|----------|---------------|
| 配置源 | `.env` 文件 | Coolify 控制台 |
| 环境变量加载 | 自动读取 `.env` | Coolify 注入 |
| Compose 文件 | `docker-compose.yml` 或 `coolify` | `docker-compose.coolify.yaml` |
| 网络 | 手动配置端口 | Coolify 自动代理 |
| HTTPS | 需手动配置 | Coolify 自动证书 |
| 日志 | `docker compose logs` | Coolify 控制台查看 |

#### 本地开发启动方式

```bash
# 1. 复制配置模板
cp .env.example .env

# 2. 编辑 .env 文件填入本地配置
vim .env

# 3. 启动服务（会自动读取 .env）
docker compose -f docker-compose.coolify.yaml up

# 或者手动指定 .env 文件
docker compose --env-file .env -f docker-compose.coolify.yaml up
```

### 13.6 常见问题排查

#### 问题 1：环境变量未生效

**症状**: 容器启动失败，日志显示“配置缺失”

**排查步骤**:
1. 在 Coolify 控制台查看 "Environment Variables" 是否已保存
2. 检查变量名是否与 Compose 文件中一致
3. 点击 "Restart" 而非 "Redeploy"（Redeploy 会重新拉取代码）
4. 查看容器日志确认变量是否被注入：
   ```bash
   docker exec <container_id> env | grep SPRING_DATASOURCE
   ```

#### 问题 2：数据库连接失败

**症状**: Backend 启动失败，日志显示 "Connection refused"

**解决方案**:
1. 确认数据库服务已启动
2. 检查 `SPRING_DATASOURCE_URL` 中的主机名：
   - Coolify 内部网络使用服务名（如 `postgres`）
   - 不要使用 `localhost` 或 `127.0.0.1`
3. 验证网络连通性：
   ```bash
   docker exec backend-container ping postgres
   ```

#### 问题 3：.env 文件配置未生效

**原因**: Coolify 不会自动加载 `.env` 文件

**解决方案**:
- 必须在 Coolify 控制台手动配置所有环境变量
- 或者使用 Coolify 的 "Bulk Import" 功能批量导入

### 13.7 安全最佳实践

#### 敏感信息管理

1. **在 Coolify 中标记 Secret**
   - 所有密码、API Key 勾选 "Secret" 选项
   - Secret 变量在日志中会被自动打码

2. **定期轮换密钥**
   - 数据库密码：每 90 天
   - API Key：每 180 天
   - S3 访问密钥：每 90 天

3. **最小权限原则**
   - 数据库用户仅授予必需权限
   - S3 Bucket Policy 限制访问范围

4. **审计日志**
   - 启用 Coolify 的访问日志
   - 定期检查环境变量修改历史

#### 网络安全

- ✅ 所有对外服务必须通过 HTTPS
- ✅ 内部服务间通信使用 Docker 内部网络
- ❌ 禁止暴露数据库端口到公网
- ❌ 禁止暴露 Redis 端口到公网

---

## 14. BGM 管理规范

### 14.1 内置 BGM 列表

**项目支持内置 BGM 列表，创建项目时自动随机选择。**

#### 存储位置
- **BGM 文件**: 存储在 S3 对象存储（Cloudflare R2 / AWS S3）
- **BGM URL 配置**: 在 `application.yml` 或 Coolify 环境变量中配置
- **数据库字段**: `projects.bgm_url` 存储项目使用的 BGM URL

### 14.2 BGM 上传流程

#### 方法 1：使用上传脚本（推荐）

```bash
# 1. 准备 BGM 文件（MP3 格式）
# 建议使用 Suno AI 生成温馨、舒适的背景音乐

# 2. 上传到 S3
./scripts/upload_bgm.sh warm-piano-01.mp3 cozy-acoustic-02.mp3 modern-minimal-03.mp3

# 3. 脚本会输出配置代码片段
```

#### 方法 2：手动上传

```bash
# 使用 AWS CLI 上传
aws s3 cp warm-piano-01.mp3 s3://ai-scene-assets/bgm/ \
  --endpoint-url=https://your-account.r2.cloudflarestorage.com \
  --content-type="audio/mpeg" \
  --acl public-read
```

### 14.3 配置 BGM 列表

#### 在 application.yml 中配置（本地开发）

```yaml
app:
  bgm:
    auto-select: true
    builtin-urls:
      - https://your-cdn.com/bgm/warm-piano-01.mp3
      - https://your-cdn.com/bgm/cozy-acoustic-02.mp3
      - https://your-cdn.com/bgm/modern-minimal-03.mp3
      - https://your-cdn.com/bgm/elegant-strings-04.mp3
      - https://your-cdn.com/bgm/sunny-guitar-05.mp3
```

#### 在 Coolify 中配置（生产环境）

**方案 A：使用 YAML 格式环境变量**

在 Coolify 控制台添加：

```yaml
# 变量名: APP_BGM_BUILTIN_URLS
# 值 (YAML 格式):
- https://your-cdn.com/bgm/warm-piano-01.mp3
- https://your-cdn.com/bgm/cozy-acoustic-02.mp3
- https://your-cdn.com/bgm/modern-minimal-03.mp3
```

**方案 B：直接修改 application.yml**

在部署后直接修改容器内的 `application.yml` 文件（不推荐，重启会丢失）

### 14.4 BGM 选择机制

#### 自动选择逻辑

1. **创建项目时**：
   ```java
   // ProjectService.createProject()
   if (bgmConfig.isAutoSelect() && bgmConfig.hasBuiltinBgm()) {
       String bgmUrl = bgmConfig.getRandomBgmUrl(); // 随机选择
       project.setBgmUrl(bgmUrl);
   }
   ```

2. **渲染视频时**：
   - 从 `projects.bgm_url` 读取 BGM URL
   - 传递给 Engine 渲染任务
   - Engine 下载 BGM 并混音

#### 禁用自动选择

```bash
# 在 Coolify 或 .env 中设置
APP_BGM_AUTO_SELECT=false
```

禁用后：
- 项目创建时 `bgm_url` 为 `null`
- 视频渲染时无 BGM（仅 TTS 音频）
- 用户可手动上传 BGM（待实现）

### 14.5 BGM 文件规范

#### 文件格式
- **推荐格式**: MP3 (192kbps 或 320kbps)
- **支持格式**: MP3, WAV, AAC
- **不推荐**: FLAC, ALAC（文件过大）

#### 音频参数
- **时长**: 2-3 分钟（支持自动循环）
- **音量**: -18dB 到 -12dB（避免过响）
- **混音音量**: 代码中自动降至 15% (`BGM_VOLUME=0.15`)

#### 文件命名规范
```
风格-乐器-序号.mp3

示例：
warm-piano-01.mp3
cozy-acoustic-02.mp3
modern-minimal-03.mp3
elegant-strings-04.mp3
sunny-guitar-05.mp3
```

### 14.6 BGM 风格指南

#### 推荐风格列表

| 风格 | 适用场景 | Suno 提示词关键词 |
|------|----------|----------------------|
| 温馨钢琴 | 通用、家庭房 | warm piano, cozy, gentle melody |
| 舒适原声 | 自然采光 | acoustic guitar, airy, natural light |
| 现代极简 | 轻奢公寓 | minimalist, modern classical, elegant |
| 优雅弦乐 | 高端住宅 | strings, sophisticated, luxury |
| 阳光治愈 | 江景房、阳台 | healing music, sunny, hopeful |

#### Suno 生成模板

```
温馨生活房产视频 BGM：

风格：轻音乐 (Light Music)、氛围音乐 (Ambient)
情绪：温馨 (Cozy)、希望 (Hopeful)、平静 (Peaceful)
乐器：钢琴主旋律、轻柔的弦乐、温暖的原声吉他
节奏：慢速 70-90 BPM
时长：2-3 分钟循环版本
关键词：warm piano, soft strings, acoustic guitar, cozy home, real estate background music, gentle melody, hopeful atmosphere
```

### 14.7 故障排查

#### 问题 1：创建项目时未自动选择 BGM

**症状**: `projects.bgm_url` 为 `null`

**排查**:
1. 检查 `APP_BGM_AUTO_SELECT` 是否为 `true`
2. 检查 `application.yml` 中 `app.bgm.builtin-urls` 是否配置
3. 查看日志：`BgmConfig.getBuiltinCount()` 返回值

#### 问题 2：BGM 下载失败

**症状**: 渲染时报错 "Failed to download BGM"

**解决**:
1. 验证 BGM URL 可访问性：`curl -I <bgm_url>`
2. 检查 S3 Bucket 权限（必须公开可读）
3. 检查 CDN 配置（如果使用）

#### 问题 3：BGM 音量过大或过小

**调整方法**:
```bash
# 在 Coolify 或 .env 中设置
BGM_VOLUME=0.10  # 默认 0.15，范围 0.05-0.30
```

### 14.8 最佳实践

#### BGM 列表管理

1. **数量控制**
   - 推荐 5-10 首 BGM
   - 过多会增加配置复杂度
   - 过少会降低随机性

2. **风格多样性**
   - 混合不同风格（钢琴、吉他、弦乐）
   - 适配不同房型（家庭房、公寓、别墅）

3. **版权合规**
   - ✅ 使用 Suno AI 生成（自动获得商用授权）
   - ✅ 使用无版权音乐库（如 Pixabay, FreePD）
   - ❌ 禁止使用未授权的商业音乐

4. **性能优化**
   - BGM 文件大小控制在 2-5MB
   - 使用 CDN 加速分发
   - 定期清理未使用的 BGM 文件
