太好了，基础设施已经就绪（假设你已经填好了配置）。现在我们进入最具挑战性、也最核心的 **Phase 3: AI 视觉引擎 (AI Engine)**。

我们将构建一个 Python 微服务，它像一个不知疲倦的剪辑助理，时刻盯着 Redis 队列，一旦有新视频上传，就立即开始工作。

### 核心任务拆解

1.  **Worker 框架搭建 (Python)**
    *   **Celery**: 分布式任务队列，负责从 Redis 领任务。
    *   **FastAPI**: 虽然 Worker 主要是后台跑，但我们可以预留一个 API 接口用于调试或健康检查。
    *   **Redis**: 连接 Upstash Redis。

2.  **视觉大模型集成 (Vision LLM)**
    *   **Qwen-VL-Plus (通义千问)**: 我们的“眼睛”。
    *   **DashScope SDK**: 阿里云官方 Python SDK。
    *   **Prompt Engineering**: 调教模型，让它不仅识别出“这是客厅”，还要识别出“采光极好、落地窗、现代简约风格”。

3.  **视频预处理 (Video Pre-processing)**
    *   **OpenCV**: 从视频中抽取关键帧（不需要把整个视频发给大模型，太贵且慢）。我们采取“均匀采样 + 关键帧提取”策略。

4.  **智能排序逻辑 (Smart Sort)**
    *   实现核心业务规则：`门头 -> 客厅 -> 餐厅 -> 厨房 -> 卫生间 -> 卧室 -> 阳台`。

***

### 实施步骤

1.  **环境初始化**: 在 `engine/` 目录下创建 `requirements.txt` 和 `Dockerfile`。
2.  **代码实现**:
    *   `engine/config.py`: 配置 Redis 和 DashScope API Key。
    *   `engine/worker.py`: Celery 应用入口。
    *   `engine/tasks.py`: 定义 `analyze_video` 任务。
    *   `engine/vision.py`: 封装 Qwen-VL 调用逻辑。
3.  **联调**: 在 Spring Boot 中触发任务，Python Worker 消费任务并打印结果。

请确认是否开始 Phase 3 的开发？
