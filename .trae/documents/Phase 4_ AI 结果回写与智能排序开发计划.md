收到。我们目前的进度是完成了 **Phase 3: AI 视觉引擎** 的核心逻辑（Engine 侧和 Backend 侧的任务触发）。

接下来我们将进入 **Phase 4: 视频渲染引擎 (Render Engine)**，但为了让整个链路真正跑通，我们需要先完善 AI 视觉分析后的**数据回写**逻辑。

目前 `engine/tasks.py` 里的 `analyze_video_task` 只是打印了日志，并没有把 AI 识别出的 `scene` 和 `features` 写回数据库。

### 阶段 4 任务规划 (完善 AI 回调与渲染准备)

1.  **Engine 侧回写数据库**
    *   在 Python Worker 中，任务完成后需要更新 `assets` 表，填入 `scene_label` 和 `scene_score`。
    *   为了遵循架构原则（Worker 不直连 DB），或者为了简化 MVP，我们需要决定回写策略。
        *   **策略 A (推荐)**: Worker 调用 Backend 的内部 API (`POST /internal/assets/{id}/analysis`) 回写结果。
        *   **策略 B**: Worker 直连 Supabase (PG)。考虑到 Python 直连 PG 很方便，且我们有统一的 DB 凭据，MVP 阶段可以直接更新 DB，减少 Backend 接口开发量。
        *   **决策**: 鉴于 MVP 的快速交付，我们采用 **策略 B (Worker 直连 Supabase)**。

2.  **智能排序逻辑 (Smart Sort)**
    *   当一个项目的所有素材都分析完毕后，需要触发“智能排序”。
    *   在 Backend 实现一个 `sortTimeline(projectId)` 方法，根据 `scene_label` 对素材进行重排。

3.  **脚本生成 (Script Generation)**
    *   基于排序后的 Timeline，调用 LLM (Qwen) 生成解说词脚本。

### 实施步骤

1.  **Engine**: 修改 `engine/tasks.py`，使用 `psycopg2` 或 `sqlalchemy` 连接 Supabase，更新 `assets` 表。
2.  **Backend**: 实现 `GET /api/v1/projects/{id}/timeline` 接口，包含简单的智能排序逻辑（如果 AI 还没分析完，就按默认顺序）。
3.  **Engine**: (可选) 增加一个 `generate_script_task`，用于后续生成脚本。

请确认是否先执行 **Step 1: Engine 回写数据库**？
