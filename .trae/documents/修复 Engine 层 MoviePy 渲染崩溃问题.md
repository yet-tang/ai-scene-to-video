# 修复 Engine 层 MoviePy 渲染崩溃问题

## 问题分析
用户反馈 `ai-scene-engine` 服务在执行 `render_pipeline_task` 时频繁报错，错误堆栈指向 `video_render.py` 中的 `clip.fx(vfx.time_mirror)`。
- **根本原因**：`MoviePy` 的 `time_mirror`（倒放）特效在初始化时会尝试读取 `t=0` 时刻的帧，而倒放后的 `t=0` 对应原视频的 `t=duration`（结束时刻）。
- **技术细节**：由于 FFMPEG 编解码的特性或元数据误差，直接读取视频**精确末尾**（`duration`）的帧往往会失败（EOF 错误），导致 `OSError: failed to read the first frame`。
- **现有缺陷**：
    1. `_open_video_clip` 中的校验逻辑存在 Bug：`min(0.1, max(0.0, duration - 0.001))` 实际上只校验了视频开头的 0.1秒，完全没有校验视频末尾是否可读。
    2. “回旋镖”逻辑（Boomerang Effect）直接对原始 `clip` 进行倒放，没有预留安全边距，极易命中 EOF 问题。

## 解决方案
我们将采取**防御性编程**策略，通过两层防护彻底解决此问题：

### 1. 修正 `_open_video_clip` 校验逻辑 (engine/video_render.py)
修改视频打开时的完整性检查，强制校验视频**头部**和**尾部**均可读取。如果尾部不可读，该视频将被视为损坏（后续逻辑会自动回退到占位符，避免崩溃）。

### 2. 增加“回旋镖”逻辑的安全裁剪 (engine/video_render.py)
在执行 `time_mirror` 倒放循环之前，主动将视频素材裁剪掉末尾的 **0.1秒**。这能确保倒放时读取的是存在的帧，彻底规避 EOF 边缘情况。

## 实施计划
1.  **编辑 `engine/video_render.py`**：
    -   修改 `_open_video_clip` 方法，修复校验时间点的计算逻辑。
    -   修改 `render_video` 方法，在进入 `while` 循环前，对 `clip` 进行安全裁剪 (`subclip(0, duration - 0.1)`)。

此方案不需要引入新的依赖，风险极低，且能覆盖绝大多数导致此类崩溃的边缘情况。