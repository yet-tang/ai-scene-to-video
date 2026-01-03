我将为您实现基于 **PySceneDetect (镜头检测) + Qwen-VL (语义合并)** 的“理想生产版”智能分段方案。

### 1. 依赖更新 (Engine)
- 修改 `engine/requirements.txt`:
  - 新增 `scenedetect` (用于检测镜头边界)。
  - 确认 `opencv-python-headless` 已存在 (scenedetect 需要)。

### 2. 视觉模块升级 (`engine/vision.py`)
- **新增 `detect_video_shots` 方法**:
  - 使用 `ContentDetector` 算法检测视频中的视觉转场（Cut detection）。
  - 返回物理镜头列表：`[(start_time, end_time), ...]`。
- **新增 `analyze_shot_grouping` 方法**:
  - 接收一组镜头关键帧图片。
  - 构建 **多图 Prompt**: "这是一组连续的视频镜头关键帧，请分析并将属于同一场景（如同一个客厅的不同角度）的镜头合并，返回合并后的语义分段（时间范围+场景标签）。"
  - 调用 Qwen-VL-Plus/Max 进行分析。

### 3. 任务流程重构 (`engine/tasks.py`)
- **修改 `analyze_video_task`**:
  - 引入新的策略分支 `SMART_SPLIT_STRATEGY = 'hybrid'` (混合模式)。
  - **Step 1**: 下载视频到本地。
  - **Step 2 (物理切分)**: 调用 `detect_video_shots` 获取基础镜头段（如 10 段）。
  - **Step 3 (视觉采样)**: 对每个镜头段提取**中间帧**。
  - **Step 4 (语义合并)**: 将 10 张图打包发给 Qwen-VL，要求其合并为 N 个场景（如 3 个：客厅、厨房、卧室）。
  - **Step 5 (执行切分)**: 根据模型返回的**合并后时间轴**，使用 `MoviePy` 切割视频。
  - **Step 6 (入库)**: 上传新片段，软删除原视频，写入 Assets 表。

### 4. 配置更新 (`engine/config.py`)
- 设置 `SMART_SPLIT_STRATEGY` 默认为 `hybrid`。
- 增加 `SCENE_DETECT_THRESHOLD` (默认 27.0) 用于控制镜头检测灵敏度。

### 预期效果
相比纯大模型分段，此方案：
1.  **更精准**: 边界由图像算法确定，不会出现“切在半句话/半个动作”中间。
2.  **更省 Token**: 只发送关键帧图片，而非整个视频流。
3.  **更有逻辑**: 先物理拆解再语义聚合，符合人类剪辑思维。