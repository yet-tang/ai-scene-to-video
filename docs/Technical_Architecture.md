# AI Scene to Video - 技术架构蓝图 (Technical Architecture Blueprint)

## 1. 需求解构与澄清 (Deconstruct & Clarify)

在动手写代码之前，我们要先看清战场的全貌。

### 1.1 核心挑战
1.  **大文件传输与存储**：用户上传多个500MB视频，带宽和存储是瓶颈。
2.  **异步处理链条**：从“上传 -> 转码 -> 视觉识别 -> 脚本生成 -> 合成”，这是一个漫长的链路。HTTP请求不能等，必须全异步。
3.  **AI 幻觉控制**：Vision LLM 可能会把“带窗户的卫生间”识别成“卧室”。我们需要在数据层保留用户“手动修正”的绝对权力。
4.  **合成效率**：FFmpeg 在服务器端渲染视频极消耗资源，必须通过队列控制并发，防止服务器雪崩。

### 1.2 关键决策
我们不做“大而全”的视频编辑器，我们做的是**流水线工厂**。

---

## 2. 架构定调 (Architectural Vision)

基于当前的业务规模（MVP阶段）和未来的扩展性，我决定采用 **“前后端分离 + 异构计算微服务”** 的架构模式。

**为什么？**
单纯的 Java/Go 处理业务逻辑很强，但在 AI 和视频处理生态上，Python 是绝对的王者。我们不能用战术上的勤奋（用 Java 硬写 AI 调用）去掩盖战略上的懒惰。

*   **业务中台 (Commander)**: 负责用户管理、状态流转、数据存储。使用 Java (Spring Boot)。
*   **AI & 渲染引擎 (Worker)**: 负责“脏活累活”——看视频、写脚本、剪视频。使用 Python (FastAPI + Celery)。
*   **消息总线**: 两者通过 Redis Message Queue 解耦。

这套架构在字节跳动早期的视频处理流水线中被验证过无数次，稳如磐石。

---

## 3. 技术栈选型与论证 (Tech Stack Decision)

这是我为你敲定的最终技术栈，不接受反驳，这是目前的最优解。

### 3.1 前端 (Client)
*   **框架**: **Vue 3 + TypeScript**
    *   *理由*: 咱们的目标用户是经纪人，大概率在微信里或者手机浏览器打开。Vue 3 的包体积小，性能好，且国内生态无敌。
*   **UI 组件库**: **Vant UI**
    *   *理由*: 有赞出品，专门针对移动端 H5 优化，组件交互非常成熟，像“拖拽排序”这种核心需求，Vant 有现成的方案。

### 3.2 后端 (Server - Business)
*   **框架**: **Spring Boot 3 + JDK 17**
    *   *理由*: 既然要上企业级，稳定压倒一切。Spring Boot 3 的生态能让我们快速集成存储、数据库和安全认证。
*   **数据库**: **PostgreSQL**
    *   *理由*: 相比 MySQL，PG 对 JSON 类型的支持是碾压级的。我们需要存储 AI 分析出来的复杂结构（场景标签、时间戳、置信度），直接存 JSONB 字段查询效率极高。
*   **缓存/队列**: **Redis**
    *   *理由*: 既做缓存，又做轻量级消息队列。MVP 阶段没必要引入 Kafka/RocketMQ 增加运维负担。

### 3.3 AI 与 视频引擎 (Engine)
*   **语言**: **Python 3.10**
*   **视觉大模型 (Vision LLM)**: **Qwen-VL-Plus (阿里云通义千问)**
    *   *理由*: 既然你是做中国市场，Qwen 是目前中文理解能力和图像识别能力综合性价比最高的模型，且 API 响应速度优于 GPT-4o。
*   **视频处理**: **FFmpeg**
    *   *理由*: 视频处理界的“瑞士军刀”，没有替代品。
*   **文本转语音 (TTS)**: **Edge TTS (免费/开源)** 或 **阿里云/Azure TTS (付费)**
    *   *理由*: MVP 建议先用 Edge TTS 验证流程，后续为了追求“专业房产顾问音色”，切到 Azure 的 Neural TTS。

### 3.4 基础设施
*   **对象存储**: **MinIO (本地开发) / 阿里云 OSS (生产)**
    *   *理由*: 视频绝对不能存磁盘，必须上对象存储。
*   **部署**: **Docker Compose**
    *   *理由*: 一键拉起所有服务，保证开发环境与生产环境一致。

---

## 4. 数据模型设计 (Data Modeling)

数据结构决定了系统的灵魂。我们需要三张核心表。

### 4.1 Projects (项目表)
存储一次视频制作任务的生命周期。

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `id` | UUID | 主键 |
| `user_id` | BIGINT | 用户ID |
| `title` | VARCHAR | 小区名 (如: 阳光花园) |
| `house_info` | JSONB | 房源详情 {room: 2, hall: 1, area: 89, price: 350} |
| `status` | VARCHAR | 状态: DRAFT, UPLOADING, ANALYZING, REVIEW, RENDERING, COMPLETED, FAILED |
| `script_content` | TEXT | 生成的解说词脚本 |
| `final_video_url`| VARCHAR | 最终成品地址 |
| `created_at` | TIMESTAMP| 创建时间 |

### 4.2 Assets (素材表)
存储用户上传的原始视频片段及 AI 分析结果。

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `id` | UUID | 主键 |
| `project_id` | UUID | 关联项目ID |
| `oss_url` | VARCHAR | 原始视频存储地址 |
| `duration` | FLOAT | 时长(秒) |
| `scene_label` | VARCHAR | AI识别结果: living_room, kitchen, bedroom... |
| `scene_score` | FLOAT | 识别置信度 |
| `user_label` | VARCHAR | 用户修正后的标签 (优先使用此字段) |
| `sort_order` | INT | 排序权重 |
| `is_deleted` | BOOLEAN | 是否被用户软删除 |

### 4.3 RenderJobs (渲染任务表)
用于追踪 FFmpeg 的处理进度。

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `id` | UUID | 主键 |
| `project_id` | UUID | 关联项目 |
| `progress` | INT | 进度 0-100 |
| `error_log` | TEXT | 错误日志 |

---

## 5. API 接口规约 (API Specification)

我们要定义一套清晰的 RESTful API，供前端调用。

### 5.1 项目与上传
*   **POST /api/v1/projects**
    *   *功能*: 创建新项目，提交基础信息（小区、户型等）。
    *   *Response*: `{ "project_id": "..." }`
*   **POST /api/v1/projects/{id}/assets**
    *   *功能*: 上传视频文件（支持 Multipart）。后端接收后上传 OSS，并生成 Asset 记录。

### 5.2 智能分析
*   **POST /api/v1/projects/{id}/analyze**
    *   *功能*: 触发 AI 分析流程。
    *   *逻辑*: 将 project_id 丢入 Redis 队列，Python Worker 消费消息，调用 Vision LLM 更新 Assets 表的 `scene_label`。

### 5.3 编排与确认 (Review)
*   **GET /api/v1/projects/{id}/timeline**
    *   *功能*: 获取“智能分段确认页”所需数据。
    *   *Response*: 包含排序后的素材列表、预生成的脚本。
*   **PUT /api/v1/projects/{id}/timeline**
    *   *功能*: 用户保存调整后的顺序、标签或修改后的脚本。
    *   *Body*: `{ "assets": [{id, sort_order, user_label}...], "script": "..." }`

### 5.4 生成
*   **POST /api/v1/projects/{id}/render**
    *   *功能*: 触发最终渲染。
    *   *逻辑*: 异步任务。Python Worker 下载素材 -> 剪辑 -> 合成语音/字幕/BGM -> 上传成品 -> 更新 Project 状态。

---

## 6. 任务拆解与开发路线图 (Task Breakdown & Roadmap)

为了保证交付，我将项目拆解为 5 个里程碑。

### Phase 1: 地基搭建 (Infrastructure)
*   [ ] **Task 1.1: 初始化 Monorepo 仓库**
    *   建立 `backend/` (Spring Boot) 和 `engine/` (Python) 目录结构。
*   [ ] **Task 1.2: 配置 Docker Compose 环境**
    *   编写 `docker-compose.yml`，包含 PostgreSQL, Redis, MinIO 服务。

### Phase 2: 核心业务后端 (Core Backend)
*   [ ] **Task 2.1: 数据库设计与迁移**
    *   使用 Flyway 或 JPA 自动生成上述数据库表结构。
*   [ ] **Task 2.2: 实现文件上传服务**
    *   集成 MinIO SDK，实现视频流式上传接口。
*   [ ] **Task 2.3: 实现项目管理 API**
    *   完成 CRUD 接口。

### Phase 3: AI 视觉引擎 (AI Engine)
*   [ ] **Task 3.1: Python Worker 框架搭建**
    *   使用 Celery + Redis 监听任务队列。
*   [ ] **Task 3.2: 集成 Qwen-VL 视觉模型**
    *   实现 `SceneDetector` 类：截取视频关键帧 -> 调用大模型 -> 返回场景标签。
*   [ ] **Task 3.3: 智能排序算法**
    *   实现规则逻辑：`Gate -> Living -> Kitchen -> Bedroom -> Balcony`。

### Phase 4: 视频渲染引擎 (Render Engine)
*   [ ] **Task 4.1: 脚本生成与 TTS**
    *   集成 LLM 生成解说词，集成 Edge-TTS 生成 mp3。
*   [ ] **Task 4.2: FFmpeg 自动化剪辑**
    *   编写 Python 脚本，根据 timeline 拼接视频、混音、烧录字幕。

### Phase 5: 前端实现 (Frontend)
*   [ ] **Task 5.1: 基础信息录入页** (Vant Form)。
*   [ ] **Task 5.2: 智能排序交互组件** (Vant Drag)。
*   [ ] **Task 5.3: 视频预览与下载页**。
