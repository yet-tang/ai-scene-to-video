# 项目规则（ai-scene-to-video）

本规则用于约束本仓库的开发/改动方式，避免引入与当前工程形态冲突的实现。

## 1. 仓库结构与职责边界

- `backend/`：Java 17 + Spring Boot 3（业务编排、状态机、DB/Redis/S3 访问、对外 HTTP API）
- `engine/`：Python 3.10 + Celery（耗时任务：视觉分析、脚本/音频生成、渲染合成）
- `frontend/`：Vue 3 + TypeScript + Vite + Vant（H5 前端）
- `.trae/rules/`：仓库开发规则（本文件 + dev_rules_*）

原则：
- `backend` 必须无状态，状态下沉到 Postgres/Redis/S3。
- `engine` 只做 CPU/GPU/FFmpeg/AI 等重任务，不直接承载对外流量（目前以 Celery Worker 形式运行）。

## 2. 本地开发与常用命令

### 2.1 Docker Compose（推荐的一键方式）

在仓库根目录：

```bash
docker compose -f docker-compose.coolify.yaml up --build
```

说明：
- 该 Compose 文件面向 Coolify 场景，DB/Redis/S3 连接通过环境变量注入，本地运行前需先准备对应依赖服务。

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
