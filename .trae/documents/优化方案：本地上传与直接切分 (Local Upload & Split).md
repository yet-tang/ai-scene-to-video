您提出的“先上传到本地切分，再上传切片”的方案是**可行的**，且对于**长视频场景**来说非常合理。

当前流程：
1. 用户 -> (上传 500MB) -> R2
2. Worker -> (下载 500MB) -> 本地切分
3. Worker -> (上传 10 个 50MB 切片) -> R2

您期望的流程（本地切分）：
1. 用户 -> (上传 500MB) -> 本地/Backend 临时目录
2. Worker/Backend -> (直接读取本地文件) -> 本地切分
3. Worker -> (上传 10 个 50MB 切片) -> R2
*(节省了一次 Worker 下载 500MB 的带宽和时间)*

考虑到我们已经实现了前后端分离和 Worker 异步架构，我为您设计了如下实施方案：

### 方案：混合上传策略 (Hybrid Upload Strategy)

**核心逻辑**：
后端 `uploadAsset` 接口将支持文件直接写入本地临时目录（Shared Volume 或本地磁盘），并直接将**本地路径**传给 Worker，Worker 识别到是本地路径则跳过下载，直接处理。

#### 1. Backend 改造 (`ProjectService.java`)
- 修改 `uploadAsset` 逻辑：
  - 不再强制调用 `storageService.uploadFile` 上传 R2。
  - 而是先将 `MultipartFile` 保存到本地临时目录（如 `/tmp/ai-video-uploads/`）。
  - 创建 Asset 记录时，`ossUrl` 字段暂时存入本地文件路径（如 `file:///tmp/...`）。
  - 发送给 Worker 的任务参数中，`video_url` 即为该本地路径。

#### 2. Engine 改造 (`tasks.py`)
- 修改 `analyze_video_task` 中的 `_download_to_temp` 逻辑：
  - 增加判断：如果 `video_url` 以 `file://` 开头，直接返回去掉了前缀的路径，**跳过下载**。
  - 这样 `ffmpeg` / `scenedetect` 可以直接读取本地大文件进行切分。

#### 3. 后续处理 (Cleanup)
- 切分完成后，原长视频文件（本地临时文件）可以被删除。
- 切分出的短视频片段（Clips）依然上传到 R2（保持原逻辑），并更新数据库中的 `oss_url` 为 R2 链接，确保前端能访问。

#### 4. 前端适配
- 前端目前的 `Presigned URL` 直传模式是为了减轻服务器带宽压力。
- **注意**：如果要改回“上传到本地”，前端必须切回 `FormData` 上传模式（即使用 `uploadAsset` 接口而非 `presign` 流程）。
- **权衡**：如果部署环境 Worker 和 Backend 在同一台机器（Docker Compose），此方案效率极高。如果是分布式部署，则不适用（需要共享存储）。鉴于您是 MVP 阶段（单机），此方案非常合适。

### 待执行任务
1.  **前端 (`CreateProject.vue`)**: 回退/切换为 `FormData` 上传模式。
2.  **后端 (`ProjectService.java`)**: 实现“保存到本地 -> 传本地路径给 Worker”的分支逻辑。
3.  **引擎 (`tasks.py`)**: 适配 `file://` 协议，跳过下载步骤。
4.  **清理**: 确保任务完成后删除本地大文件。