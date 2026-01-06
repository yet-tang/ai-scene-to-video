# 方案A：以 Object Key 为真源的存储与渲染链路改造

## 目标

将“可播放的 public URL”与“对象存储中的真实对象”解耦：以 `bucket + object_key`（或本地路径）作为系统内的唯一真相，保证引擎侧渲染/分析不再依赖不稳定的 HTTP 公网 URL，从根上消除“下载到错误页/截断文件导致 MoviePy/FFmpeg 报损坏”的随机故障模式。

## 约束假设

- 上传与渲染为低频任务（单项目分钟级），系统整体 QPS < 100 的量级。
- 单文件可达数百 MB；对象存储为 Cloudflare R2（S3 兼容）。
- 允许引入少量开发复杂度换取运行稳定性与可观测性。

## 问题复盘（现状不稳的根因）

1. `assets.oss_url` 混合承载了多种语义：`file://` 本地路径、R2 public URL、后端本地 HTTP URL。引擎侧只能靠启发式判断如何下载，易错且不可控。
2. 引擎通过 HTTP 拉取 public URL：任何鉴权/防盗链/CDN/域名解析/证书/跨网段访问问题，都会被“静默”转化为落盘的 HTML/XML 错误页或截断文件，最终以 MoviePy 的“failed to read first frame”形式爆炸，排查困难。
3. DB 不存 `object_key`：导致无法稳定走 S3 API 拉取，也无法在更换 public 域名/CDN 前缀时保持引擎不受影响。

## 总体方案

- **存储真相**：`storage_type + storage_bucket + storage_key`（或 `local_path`）作为引擎侧下载依据。
- **展示 URL**：`oss_url` 仅用于前端展示/预览或兼容，禁止引擎依赖它完成渲染与分析。
- **引擎下载策略**：对 S3/R2 永远使用 S3 API（boto3 / AWS SDK）下载到本地临时文件；HTTP 下载仅作为历史数据兼容路径，并必须带完整性校验与重试。

## 数据模型改造（Postgres / Flyway）

在 `assets` 表新增（保留 `oss_url` 不删）：

- `storage_type VARCHAR(32) NOT NULL DEFAULT 'S3'`
  - 取值建议：`S3` / `LOCAL_FILE` / `HTTP_URL`（仅用于历史兼容）
- `storage_bucket VARCHAR(255) NULL`
- `storage_key VARCHAR(1024) NULL`
- （可选但推荐）`local_path VARCHAR(1024) NULL`：仅在 `LOCAL_FILE` 使用

迁移示意：

```sql
ALTER TABLE assets
    ADD COLUMN storage_type VARCHAR(32) NOT NULL DEFAULT 'S3',
    ADD COLUMN storage_bucket VARCHAR(255),
    ADD COLUMN storage_key VARCHAR(1024),
    ADD COLUMN local_path VARCHAR(1024);
```

约束建议（可逐步加严）：

- 新写入资产必须满足：
  - `storage_type='S3'` 时 `storage_key IS NOT NULL`
  - `storage_type='LOCAL_FILE'` 时 `local_path IS NOT NULL`

## 后端改造（Spring Boot）

### 1）Presigned PUT 上传链路

现有接口：

- `POST /v1/projects/{id}/assets/presign`：返回 `objectKey + uploadUrl + publicUrl`
- `POST /v1/projects/{id}/assets/confirm`：写入资产记录

改造要点：

- `confirm` 时写入：
  - `storage_type='S3'`
  - `storage_bucket = 配置的 bucket`
  - `storage_key = request.objectKey`
  - `oss_url = storageService.getPublicUrl(objectKey)`（仅用于前端展示/兼容）
- 下发给引擎的任务参数应携带 `storage_*` 字段（见“引擎改造”）。

### 2）直传（Multipart）上传链路

现有接口：

- `POST /v1/projects/{id}/assets`：优先落本地 `/tmp/ai-video-uploads`，失败才上传 S3
- `POST /v1/projects/{id}/assets/local`：落本地并返回后端可访问 URL

改造要点：

- 若最终落 S3：
  - 写入 `storage_type='S3'`、`storage_key`（对象名）、`storage_bucket`，同时填 `oss_url` 供前端预览。
- 若落本地：
  - 写入 `storage_type='LOCAL_FILE'`、`local_path='/tmp/ai-video-uploads/xxx.mp4'`
  - `oss_url` 可继续写 `file://...` 或后端公开静态路径，但引擎不再依赖该字段。

### 3）前端播放（可选增强）

对于桶非公开读或希望更强安全控制的场景，建议新增：

- `GET /v1/projects/{id}/assets/{assetId}/play-url`：后端生成 **Presigned GET**（有效期 ≤ 1h）返回给前端播放。

前端播放策略：

- 推荐优先使用后端返回的 Presigned GET URL。
- DB 中的 `oss_url` 仅作为兜底或展示字段。

## 引擎改造（Python / Celery）

### 1）统一“本地化”入口

引擎侧新增统一函数（示意）：

```python
def materialize_asset_to_local(asset: dict) -> str:
    t = asset.get("storage_type")
    if t == "S3":
        bucket = asset.get("storage_bucket") or Config.S3_STORAGE_BUCKET
        key = asset["storage_key"]
        # boto3.download_file(bucket, key, /tmp/xxx)
        return local_path
    if t == "LOCAL_FILE":
        return asset["local_path"]
    if t == "HTTP_URL":
        # 兼容旧数据：HTTP 下载 + 校验 + 重试
        return local_path
    raise ValueError("unknown storage_type")
```

规则：

- **渲染与分析只接受“本地文件路径”作为后续处理输入**。
- 对 `S3` 永远走 S3 API 下载，不依赖 `oss_url` 可公网访问。
- 对 `HTTP_URL`（历史兼容）必须：
  - 下载重试（至少 3 次）
  - 快速判别是否是 HTML/XML 错误页
  - `ffprobe` 能解析出视频流，否则判定下载不可信并失败重试

### 2）任务参数与 DB 读取

引擎当前通过 DB 查询资产（`SELECT id, oss_url, duration...`）。改造为：

- 查询并携带：
  - `storage_type`
  - `storage_bucket`
  - `storage_key`
  - `local_path`
  - `oss_url`（可选，仅作兼容）

引擎内部从 DB 取到 asset dict 后，统一调用 `materialize_asset_to_local` 获得路径，再交给 OpenCV/MoviePy/FFmpeg。

### 3）渲染尺寸与占位片段

占位片段尺寸必须与最终输出尺寸一致（或可推导至一致的缩放策略），避免 `compose` 时出现黑边/变形/尺寸不一致导致的额外不稳定。

建议策略：

- 统一输出高度（例如 720），宽度按源视频等比换算；
- 第一段可用视频作为“输出尺寸锚点”；占位片段随锚点尺寸生成/调整。

## 兼容与迁移策略（老数据）

### 1）双写阶段（推荐）

上线后端改造时：

- 新上传资产写入 `storage_*` 与 `oss_url`。
- 引擎优先走 `storage_*`；若缺失则回退到旧 `oss_url` 兼容逻辑（但必须严格校验下载结果）。

### 2）历史数据回填

对满足 `storage_key IS NULL AND oss_url IS NOT NULL` 的行：

- `oss_url` 为 `file://...`：回填 `storage_type='LOCAL_FILE'`、`local_path=...`
- `oss_url` 为 R2/AWS public URL：解析出 `bucket + key`：
  - host 形如 `{bucket}.xxx.r2.cloudflarestorage.com`：`key = path.lstrip('/')`
  - path 形如 `/{bucket}/{key}`：提取 bucket 与 key
  - 解析失败的行输出清单人工处理

## 可观测性与运维挑战（必须提前认清）

### 潜在坑点

- 若引擎与后端使用不同的 S3/R2 凭据或 endpoint 配置，下载会系统性失败；必须在部署层保证一致。
- 本地上传 (`LOCAL_FILE`) 只有在引擎与后端共享同一文件系统/容器卷且路径一致时才成立；否则只能退回 S3。
- 回填历史 URL 解析可能存在多种 URL 形态，解析失败必须有兜底与人工处理流程。

### 观测建议

下载失败日志必须包含（结构化字段）：

- `storage_type`, `bucket`, `key`（或 `url_host`）
- 下载耗时、下载字节数
- `ffprobe` 失败摘要（控制长度）

严禁打印包含签名的完整 presigned URL（避免泄漏）。

## 为什么这个方案更稳

- 引擎侧不再依赖 public URL 可读性（CDN/鉴权/跨网段）这一脆弱条件。
- 更换 public 域名、调整 CDN 策略、桶改为私有读，都不会影响渲染/分析链路。
- 故障从“MoviePy/FFmpeg 读首帧失败（信息不透明）”变成“某个 bucket/key 下载失败或 ffprobe 校验失败（可定位）”。

