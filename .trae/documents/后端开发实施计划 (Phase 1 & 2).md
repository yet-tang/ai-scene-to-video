根据您的PRD和技术架构文档，我将分步骤为您搭建后端服务。

我们将遵循“业务中台 (Commander)”的设计，使用 Spring Boot 3 + JDK 17，并配合 Docker 环境。

### 阶段 1: 基础设施搭建 (Infrastructure)
1.  **Monorepo 结构初始化**
    *   创建 `backend/` (Spring Boot 项目根目录)
    *   创建 `engine/` (Python 引擎目录 - 暂时保留结构)
2.  **Docker 环境配置**
    *   编写 `docker-compose.yml`，集成 PostgreSQL (数据库), Redis (缓存/消息队列), MinIO (对象存储)。
    *   配置各服务的环境变量与端口映射。

### 阶段 2: 核心后端开发 (Core Backend)
1.  **Spring Boot 项目初始化**
    *   创建 `pom.xml`: 引入 Web, Data JPA, PostgreSQL, Lombok, MinIO 等依赖。
    *   配置 `application.yml`: 连接 Docker 中的各服务。
2.  **数据模型实现 (Domain Modeling)**
    *   根据架构文档实现实体类：`Project` (项目), `Asset` (素材), `RenderJob` (任务)。
    *   创建对应的 JPA Repository 接口。
3.  **核心服务层实现 (Service Layer)**
    *   `StorageService`: 封装 MinIO 的文件上传/下载逻辑。
    *   `ProjectService`: 处理项目创建、状态流转。
4.  **API 接口开发 (Controller Layer)**
    *   `ProjectController`: 实现创建项目、获取详情接口。
    *   `AssetController`: 实现视频素材上传接口。

完成后，我们将拥有一个可以运行的后端服务，支持创建项目和上传视频文件，为后续接入 AI 引擎打好基础。