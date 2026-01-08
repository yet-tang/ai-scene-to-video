# 针对 AI 房产短视频的“温情生活风”优化技术方案

根据您提供的《生成的视频建议.md》及阿里云通义万相 API 文档，我制定了以下技术优化方案。本方案旨在通过 AI 脚本重构、AI 视觉增强和多轨音频合成，将视频从“冷冰冰的房源介绍”升级为“有温度的生活方式种草”。

## 一、 核心架构改造 (Architecture Redesign)

我们将原有的 `脚本 -> 简单拼接` 线性流程改造为 **"语义驱动的视听增强流水线"**。

### 1. 流程对比
*   **当前 (Current):**
    *   `ScriptGenerator`: 仅生成解说词 (杭州话/口语)。
    *   `VideoRenderer`: 简单拼接视频 + TTS 音频。
*   **优化后 (Proposed):**
    *   **Phase 1: 情感化脚本引擎**: 生成解说词 + **视觉/听觉元数据** (Visual/Audio Metadata)。
    *   **Phase 2: AI 视觉重绘 (Visual Enhancer)**: 调用 `wanx2.1-vace-plus` 对关键帧/片段进行风格化重绘 (Warm/Cinematic)。
    *   **Phase 3: 多模态合成 (Compositor)**: 基于 MoviePy 实现多轨混音 (TTS + BGM + SFX) 和动态字幕渲染。

## 二、 详细实施方案 (Implementation Details)

### 1. 脚本引擎升级 (Script Engine 2.0)
*   **目标**: 实现《建议文档》中的“情绪渲染”。
*   **技术点**:
    *   更新 `engine/script_gen.py` 的 Prompt，注入“温情/治愈/阳光”风格约束。
    *   **结构化输出扩展**: 除了 `text`，增加 `visual_prompt` (用于 AI 重绘) 和 `audio_cue` (用于 SFX 触发)。
    *   **Prompt 示例**:
        > "场景：客厅。文案：'谁能拒绝一个满屋阳光的客厅呢？'。视觉指令：'Warm sunshine, cinematic lighting, cozy atmosphere'。音效指令：'Birds chirping'。"

### 2. 视觉增强子系统 (Visual Enhancement with Wanxiang)
*   **目标**: 解决“色调偏冷偏灰”问题，提升“高级感”。
*   **API 选型**: 阿里云通义万相 `wanx2.1-vace-plus`。
*   **功能映射**:
    *   **全局滤镜 (Color Grading)**: 使用 `video_repainting` (视频重绘) 接口。
        *   *Prompt*: "A cozy room filled with warm sunlight, high resolution, 4k, cinematic lighting."
        *   *Control*: 使用 `depth` (深度图控制) 保持原有家具结构不变，仅改变光影和色调。
    *   **静态图转视频**: 对于仅有照片的房间，使用 `image_to_video` 生成推拉镜头，避免 PPT 感。
*   **实现方式**: 新增 `engine/aliyun_client.py` 封装异步 HTTP 调用 (提交任务 -> 轮询状态)。

### 3. 音频与后期合成 (Audio & Post-Production)
*   **目标**: 增加 BGM 和环境音 (SFX)。
*   **技术点**:
    *   **BGM**: 在 `VideoRenderer` 中引入背景音乐轨道，支持自动闪避 (Auto-ducking) —— 当人声出现时自动降低 BGM 音量。
    *   **SFX**: 解析脚本中的 `audio_cue`，在特定时间点（如“推窗”时）叠加“鸟鸣/风声”素材。
    *   **字幕**: 使用 `moviepy` 或 `ffmpeg` 滤镜添加关键帧字幕（如“会呼吸的家”），样式设为白色细体加阴影，提升精致感。

## 三、 风险评估与应对 (Risk & Mitigation)

| 风险点 | 描述 | 应对策略 |
| :--- | :--- | :--- |
| **成本高昂** | 视频重绘 API 价格较高，且耗时较长 (5-10分钟/任务)。 | **策略**: 仅对“首帧/封面”或“高光时刻”片段进行 AI 重绘，普通片段使用 FFmpeg 传统滤镜 (ColorCurve) 进行低成本调色。 |
| **一致性问题** | AI 重绘可能导致不同片段的色温不统一。 | **策略**: 固定 Prompt 中的光照描述词；或仅在转场/特写时使用 AI，保持主叙事画面原样。 |
| **文字渲染** | AI 生成视频中的文字通常不可控/乱码。 | **策略**: **不使用** AI 生成字幕。所有字幕通过 FFmpeg/MoviePy 在后期合成阶段叠加。 |

## 四、 落地计划 (Action Plan)

1.  **Scaffold**: 创建 `engine/aliyun_client.py`，实现通义万相 API 的鉴权与调用封装。
2.  **Script**: 修改 `ScriptGenerator`，支持生成包含视觉/听觉指令的增强版脚本。
3.  **Render**: 改造 `VideoRenderer`，增加：
    *   FFmpeg 暖色滤镜 (作为低成本默认方案)。
    *   多轨音频混合逻辑。
4.  **Integration**: 在 `worker.py` 中串联流程，增加“AI 增强”开关。
