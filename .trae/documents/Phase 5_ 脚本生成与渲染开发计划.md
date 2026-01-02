太棒了，基建稳固后，我们终于可以攻克项目的最后一公里：**Phase 5: 脚本生成与最终渲染**。

这一阶段我们将让 AI 真正“开口说话”并“剪出成片”。

### 核心任务拆解

1.  **脚本生成 (Script Generation)**
    *   **Backend API**: `POST /api/v1/projects/{id}/script`。
    *   **Engine Task**: `generate_script_task`。
    *   **逻辑**: 收集所有已分析素材的 `scene_label` 和 `features`，组合成 Prompt 发送给 Qwen-Plus (LLM)，生成一段连贯的房产解说词。

2.  **语音合成 (TTS)**
    *   **Engine Task**: `generate_audio_task`。
    *   **集成**: 接入 DashScope 的语音合成 API (Sambert)，将生成的脚本转为 MP3。

3.  **视频渲染 (Video Rendering)**
    *   **Engine Task**: `render_video_task`。
    *   **工具**: 使用 `MoviePy`。
    *   **逻辑**:
        *   将所有素材按 `sort_order` 拼接。
        *   添加背景音乐（可选，先留口子）。
        *   将生成的 TTS 音频混入视频。
        *   (高级) 根据解说词长度自动调整每个素材的播放时长（MVP 先做定长或原始时长）。

### 实施步骤

1.  **Engine**:
    *   修改 `engine/tasks.py`，新增 `generate_script_task` (LLM)。
    *   新增 `generate_audio_task` (TTS)。
    *   新增 `render_video_task` (MoviePy)。
2.  **Backend**:
    *   新增 `RenderController`，用于触发脚本生成和最终渲染。
    *   更新 `ProjectService` 处理相关业务逻辑。

我们先从 **脚本生成 (LLM)** 开始，如何？
