# 核心架构与基础设施规则 (Infrastructure Rules)

## 1. 架构原则
- **微服务/单体边界**: 后端采用 Monolithic 架构 (`backend`)，但通过 Python Worker (`engine`) 剥离 CPU/GPU 密集型任务。
- **无状态**: 业务服务必须无状态，所有状态下沉至 DB/Redis/S3。
- **环境隔离**: 严禁将生产环境凭据提交至代码库，必须通过环境变量注入。

## 2. 统一依赖 (Dependencies)
- **数据库 (PostgreSQL)**
  - 必须复用 自部署的统一postgresql JDBC 连接。
  - 禁止在业务代码中执行 DDL，必须使用 Flyway/Liquibase 管理 Schema 变更。
- **对象存储 (Object Storage)**
  - 必须复用 Supabase Storage (S3 兼容)。
  - 上传大文件（>10MB）必须使用 Presigned URL 或流式上传。
- **缓存与消息 (Redis)**
  - 必须复用 自部署的统一redis。
  - 键名必须包含前缀 `ai-video:` 以防冲突。

## 3. 网络与暴露
- **公网入口**: 仅 Nginx 网关可暴露 80/443。
- **内部通信**: 服务间调用必须走内网 DNS (Docker Service Name)，禁止公网回绕。
