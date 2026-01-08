# Coolify生产部署

<cite>
**本文引用的文件**
- [COOLIFY_DEPLOY.md](file://COOLIFY_DEPLOY.md)
- [docker-compose.coolify.yaml](file://docker-compose.coolify.yaml)
- [application.yml](file://backend/src/main/resources/application.yml)
- [S3StorageConfig.java](file://backend/src/main/java/com/aiscene/config/S3StorageConfig.java)
- [config.py](file://engine/config.py)
- [integration_test.py](file://integration_test.py)
- [.env.example](file://.env.example)
- [HealthController.java](file://backend/src/main/java/com/aiscene/controller/HealthController.java)
- [build.sh](file://build.sh)
- [Dockerfile（后端）](file://backend/Dockerfile)
- [Dockerfile（引擎）](file://engine/Dockerfile)
- [Dockerfile（前端）](file://frontend/Dockerfile)
</cite>

## 目录
1. [简介](#简介)
2. [项目结构](#项目结构)
3. [核心组件](#核心组件)
4. [架构总览](#架构总览)
5. [详细组件分析](#详细组件分析)
6. [依赖关系分析](#依赖关系分析)
7. [性能考虑](#性能考虑)
8. [故障排查指南](#故障排查指南)
9. [结论](#结论)
10. [附录](#附录)

## 简介
本操作手册面向运维人员，基于仓库中的 Coolify 部署文档与 Compose 配置，提供在 Coolify 平台上完成生产级部署的完整步骤。内容涵盖：
- 如何在 Coolify 上创建 Git 关联型资源并指定 Compose 配置路径
- 四大类环境变量的正确配置方法（数据库、Redis、对象存储、AI 服务）
- docker-compose.coolify.yaml 中三个服务的构建上下文、依赖关系与网络配置
- 部署后的验证流程（含自动化集成测试）
- 常见问题排查建议（日志、变量拼写、外部服务连通性）

## 项目结构
该仓库采用多模块结构，包含后端（Java/Spring Boot）、引擎（Python/Celery）、前端（Vue/Nginx）三部分，配合统一的 Docker Compose 配置实现一键部署。

```mermaid
graph TB
subgraph "Coolify 平台"
UI["Coolify 控制台"]
Git["Git 仓库<br/>包含 docker-compose.coolify.yaml"]
Build["Docker Compose 构建器"]
Services["运行中的服务组<br/>backend/engine/frontend"]
end
subgraph "应用代码"
Backend["后端：Spring Boot 应用"]
Engine["引擎：Python Celery 任务队列"]
Frontend["前端：Vue + Nginx"]
end
subgraph "外部依赖"
DB["自建 PostgreSQL"]
Redis["自建 Redis"]
S3["S3/Cloudflare R2 存储"]
DashScope["阿里云 DashScope API"]
end
UI --> Git
Git --> Build
Build --> Services
Services --> Backend
Services --> Engine
Services --> Frontend
Backend --> DB
Backend --> Redis
Backend --> S3
Engine --> DB
Engine --> Redis
Engine --> S3
Engine --> DashScope
```

图表来源
- [docker-compose.coolify.yaml](file://docker-compose.coolify.yaml#L1-L86)
- [application.yml](file://backend/src/main/resources/application.yml#L1-L66)
- [S3StorageConfig.java](file://backend/src/main/java/com/aiscene/config/S3StorageConfig.java#L1-L61)
- [config.py](file://engine/config.py#L1-L46)

章节来源
- [docker-compose.coolify.yaml](file://docker-compose.coolify.yaml#L1-L86)
- [COOLIFY_DEPLOY.md](file://COOLIFY_DEPLOY.md#L1-L99)

## 核心组件
- 后端服务（ai-scene-backend）
  - 基于 Spring Boot，使用 JPA/Redis/Flyway/Actuator
  - 通过环境变量读取数据库、Redis、S3 等配置
  - 提供健康检查端点，支持就绪探针
- 引擎服务（ai-scene-engine）
  - 基于 Python，使用 Celery 与 Redis 作为消息队列
  - 通过环境变量读取 DashScope API Key、数据库 DSN、S3 配置
  - 依赖后端服务以完成任务调度与状态流转
- 前端服务（ai-scene-frontend）
  - 基于 Vue，构建后由 Nginx 提供静态资源
  - 通过构建参数注入后端 API 基础地址与密钥

章节来源
- [application.yml](file://backend/src/main/resources/application.yml#L1-L66)
- [S3StorageConfig.java](file://backend/src/main/java/com/aiscene/config/S3StorageConfig.java#L1-L61)
- [config.py](file://engine/config.py#L1-L46)
- [docker-compose.coolify.yaml](file://docker-compose.coolify.yaml#L1-L86)

## 架构总览
下图展示 Coolify 部署后各服务间的依赖与网络关系：

```mermaid
graph TB
subgraph "Coolify 网络 coolify"
Net["coolify 外部网络"]
B["ai-scene-backend"]
E["ai-scene-engine"]
F["ai-scene-frontend"]
end
DB["PostgreSQL"]
R["Redis"]
S3["S3/Cloudflare R2"]
DS["DashScope"]
B --> DB
B --> R
B --> S3
E --> DB
E --> R
E --> S3
E --> DS
F --> B
B --- Net
E --- Net
F --- Net
```

图表来源
- [docker-compose.coolify.yaml](file://docker-compose.coolify.yaml#L1-L86)
- [application.yml](file://backend/src/main/resources/application.yml#L1-L66)
- [S3StorageConfig.java](file://backend/src/main/java/com/aiscene/config/S3StorageConfig.java#L1-L61)
- [config.py](file://engine/config.py#L1-L46)

## 详细组件分析

### 1. 在 Coolify 上创建 Git 关联型资源并指定 Compose 路径
- 将包含 docker-compose.coolify.yaml 的最新代码推送至 GitHub/GitLab 等远端仓库
- 在 Coolify 控制台新建资源，选择“Git Based”下的“Private/Public Repository”
- 在配置页面找到“Docker Compose Location”，将其设为 /docker-compose.coolify.yaml
- Build Pack 选择“Docker Compose”

章节来源
- [COOLIFY_DEPLOY.md](file://COOLIFY_DEPLOY.md#L16-L35)

### 2. 环境变量配置（四大类）
- 数据库（Backend 与 Engine）
  - Spring Boot 方式：SPRING_DATASOURCE_URL、SPRING_DATASOURCE_USERNAME、SPRING_DATASOURCE_PASSWORD
  - 引擎方式：DB_DSN（Python 格式，形如 postgresql://user:pass@host:port/dbname）
  - 特别提示：若密码包含特殊字符，必须进行 URL 编码
- Redis
  - SPRING_REDIS_URL（Spring Boot 格式，例如 redis://default:password@host:port/0）
- 对象存储（S3/Cloudflare R2）
  - S3_STORAGE_REGION、S3_STORAGE_ENDPOINT、S3_STORAGE_ACCESS_KEY、S3_STORAGE_SECRET_KEY、S3_STORAGE_BUCKET、S3_STORAGE_PUBLIC_URL
- AI 服务（DashScope）
  - DASHSCOPE_API_KEY

章节来源
- [COOLIFY_DEPLOY.md](file://COOLIFY_DEPLOY.md#L36-L74)
- [.env.example](file://.env.example#L1-L25)
- [docker-compose.coolify.yaml](file://docker-compose.coolify.yaml#L13-L60)

### 3. docker-compose.coolify.yaml 服务解析
- ai-scene-backend
  - 构建上下文：./backend，Dockerfile
  - 端口映射：8090:8090
  - 环境变量：SERVER_PORT、数据库、Redis、S3、开发与上传相关开关
  - 健康检查：/health
  - 网络：加入 coolify 外部网络
- ai-scene-engine
  - 构建上下文：./engine，Dockerfile
  - 环境变量：REDIS_URL、DB_DSN、DASHSCOPE_API_KEY、S3、智能拆分策略等
  - 依赖：depends_on: ai-scene-backend
  - 网络：加入 coolify 外部网络
- ai-scene-frontend
  - 构建上下文：./frontend，Dockerfile
  - 构建参数：VITE_API_BASE_URL、VITE_API_KEY
  - 端口映射：3000:80
  - 依赖：depends_on: ai-scene-backend
  - 网络：加入 coolify 外部网络

```mermaid
flowchart TD
Start(["Compose 启动"]) --> BldB["构建 backend 镜像<br/>context=./backend"]
BldB --> RunB["启动 backend 容器<br/>端口 8090:8090<br/>健康检查 /health"]
Start --> BldE["构建 engine 镜像<br/>context=./engine"]
BldE --> DepE["等待 backend 就绪"]
DepE --> RunE["启动 engine 容器<br/>依赖 backend"]
Start --> BldF["构建 frontend 镜像<br/>context=./frontend"]
BldF --> DepF["等待 backend 就绪"]
DepF --> RunF["启动 frontend 容器<br/>端口 3000:80"]
RunB --> Net["加入 coolify 网络"]
RunE --> Net
RunF --> Net
```

图表来源
- [docker-compose.coolify.yaml](file://docker-compose.coolify.yaml#L1-L86)

章节来源
- [docker-compose.coolify.yaml](file://docker-compose.coolify.yaml#L1-L86)

### 4. 后端与引擎的配置要点
- 后端（Spring Boot）
  - 数据库：通过 SPRING_DATASOURCE_URL/USERNAME/PASSWORD 注入
  - Redis：通过 SPRING_REDIS_URL 注入
  - S3：通过 s3.storage.* 系列属性注入，SDK 以 endpointOverride 与 path-style 访问方式适配 R2
  - 健康检查：/health（存活探针）、/ready（就绪探针，依赖数据库校验）
- 引擎（Python）
  - Redis：REDIS_URL
  - 数据库：DB_DSN（推荐使用完整 DSN，避免分段拼接导致的 URL 编码问题）
  - S3：S3_STORAGE_* 系列
  - DashScope：DASHSCOPE_API_KEY

章节来源
- [application.yml](file://backend/src/main/resources/application.yml#L1-L66)
- [S3StorageConfig.java](file://backend/src/main/java/com/aiscene/config/S3StorageConfig.java#L1-L61)
- [config.py](file://engine/config.py#L1-L46)
- [HealthController.java](file://backend/src/main/java/com/aiscene/controller/HealthController.java#L1-L38)

### 5. 部署后的验证流程
- 在 Coolify 控制台点击 Deploy 开始构建与部署
- 部署完成后，获取 ai-scene-backend 的公开域名（若已配置域名）
- 使用 integration_test.py 进行自动化接口测试
  - 安装依赖：pip install requests
  - 运行测试：python integration_test.py https://your-backend-domain.com
  - 可选：本地先执行 build.sh 构建镜像后再测试

```mermaid
sequenceDiagram
participant Ops as "运维"
participant Coolify as "Coolify 控制台"
participant Backend as "ai-scene-backend"
participant Engine as "ai-scene-engine"
participant Frontend as "ai-scene-frontend"
participant Test as "integration_test.py"
Ops->>Coolify : 触发部署
Coolify->>Backend : 构建并启动
Coolify->>Engine : 构建并启动依赖 backend
Coolify->>Frontend : 构建并启动依赖 backend
Ops->>Test : python integration_test.py <backend-domain>
Test->>Backend : GET /health
Test->>Backend : POST /v1/projects
Test->>Backend : POST /v1/projects/{id}/assets
Test->>Backend : GET /v1/projects/{id}/timeline
Test->>Backend : POST /v1/projects/{id}/script
Test->>Backend : POST /v1/projects/{id}/audio
Test->>Backend : POST /v1/projects/{id}/render
Backend-->>Test : 返回最终视频 URL
Test->>Test : 校验音频流存在性
```

图表来源
- [COOLIFY_DEPLOY.md](file://COOLIFY_DEPLOY.md#L75-L99)
- [integration_test.py](file://integration_test.py#L1-L305)
- [docker-compose.coolify.yaml](file://docker-compose.coolify.yaml#L1-L86)

章节来源
- [COOLIFY_DEPLOY.md](file://COOLIFY_DEPLOY.md#L75-L99)
- [integration_test.py](file://integration_test.py#L1-L305)
- [build.sh](file://build.sh#L1-L27)

## 依赖关系分析
- 服务间依赖
  - engine 与 frontend 均依赖 backend（depends_on）
  - backend 与 engine 共享 coolify 外部网络
- 外部依赖
  - 数据库：PostgreSQL
  - 缓存：Redis
  - 对象存储：S3/Cloudflare R2
  - AI 服务：DashScope

```mermaid
graph LR
FE["frontend"] --> BE["backend"]
EN["engine"] --> BE
BE --> PG["PostgreSQL"]
BE --> RD["Redis"]
BE --> S3["S3/Cloudflare R2"]
EN --> DS["DashScope"]
```

图表来源
- [docker-compose.coolify.yaml](file://docker-compose.coolify.yaml#L1-L86)

章节来源
- [docker-compose.coolify.yaml](file://docker-compose.coolify.yaml#L1-L86)

## 性能考虑
- 合理设置 Redis 与数据库连接池大小，避免过载
- 对 S3 上传/下载启用合适的并发与超时策略
- 前端静态资源缓存与压缩策略，减少带宽占用
- 引擎任务队列规模与并发度需结合 CPU/内存资源评估

## 故障排查指南
- 查看容器日志
  - 在 Coolify 控制台的 Logs 选项卡查看 backend/engine 的启动日志
- 检查环境变量拼写
  - 确认 SPRING_DATASOURCE_URL/USERNAME/PASSWORD、SPRING_REDIS_URL、S3_STORAGE_*、DASHSCOPE_API_KEY 是否完整且无拼写错误
  - 特别注意 DB_DSN 的 Python 格式与密码中的特殊字符 URL 编码
- 确认外部服务连通性
  - 数据库：从 backend 容器内 ping/连接 PostgreSQL
  - Redis：从 backend/engine 容器内连接 Redis
  - S3：从 backend/engine 容器内访问 endpoint，验证 region、access/secret key、bucket 权限
  - DashScope：从 engine 容器内访问 DashScope API，确认 API Key 有效
- 健康检查失败
  - 若 /health 正常但 /ready 返回 503，检查数据库连接有效性
- 端口冲突与暴露
  - 前端默认映射 3000:80，确保宿主端口未被占用

章节来源
- [COOLIFY_DEPLOY.md](file://COOLIFY_DEPLOY.md#L82-L99)
- [HealthController.java](file://backend/src/main/java/com/aiscene/controller/HealthController.java#L1-L38)
- [docker-compose.coolify.yaml](file://docker-compose.coolify.yaml#L1-L86)

## 结论
通过以上步骤，可在 Coolify 平台上完成本项目的生产级部署。关键在于：
- 正确设置 Compose 路径与构建上下文
- 严格遵循四大类环境变量的格式与编码规范
- 明确服务间的依赖与网络配置
- 使用自动化测试脚本进行部署后验证

## 附录
- 快速参考清单
  - Compose 路径：/docker-compose.coolify.yaml
  - 后端端口：8090
  - 前端端口：3000
  - 网络：coolify（外部网络）
  - 健康检查：/health（backend）
  - 就绪检查：/ready（backend，依赖数据库）
- 本地构建与测试
  - 本地构建：./build.sh
  - 自动化测试：python integration_test.py https://your-backend-domain.com

章节来源
- [docker-compose.coolify.yaml](file://docker-compose.coolify.yaml#L1-L86)
- [build.sh](file://build.sh#L1-L27)
- [integration_test.py](file://integration_test.py#L1-L305)