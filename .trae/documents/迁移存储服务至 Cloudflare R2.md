此计划将把对象存储从 Supabase Storage 迁移到 Cloudflare R2，并标准化配置命名以支持通用的 S3 协议。

### 1. 配置标准化 (Configuration)
将所有 `SUPABASE_STORAGE_*` 环境变量重命名为 `S3_STORAGE_*`，使其兼容 R2 及其他 S3 服务。

*   **修改文件**: `.env`, `.env.example`, `backend/src/main/resources/application.yml`, `docker-compose.coolify.yaml`
*   **新变量名**:
    *   `S3_STORAGE_ENDPOINT` (R2: `https://<account_id>.r2.cloudflarestorage.com`)
    *   `S3_STORAGE_ACCESS_KEY`
    *   `S3_STORAGE_SECRET_KEY`
    *   `S3_STORAGE_BUCKET`
    *   `S3_STORAGE_REGION` (R2 固定为 `auto`)
    *   `S3_STORAGE_PUBLIC_URL` (用于访问文件的公开域名)

### 2. 后端改造 (Backend - Java)
更新 Spring Boot 的 S3 配置以适配 AWS SDK v2 和 R2 特性。

*   **重构**: 将 `SupabaseStorageConfig.java` 重命名为 `S3StorageConfig.java`。
*   **代码调整**:
    *   读取新的 `s3.storage.*` 配置属性。
    *   配置 `S3Client` 使用 `Region.of("auto")` (R2 要求)。
    *   保持 `forcePathStyle(true)` 以确保兼容性。

### 3. 引擎改造 (Engine - Python)
更新 Python Worker 以使用 `boto3` 连接 R2。

*   **修改 `engine/config.py`**: 读取新的 `S3_STORAGE_*` 环境变量。
*   **修改 `engine/tasks.py`**:
    *   引入 `boto3`。
    *   **实现缺失的 `upload_to_s3` 函数**：构建 S3 Client 并上传渲染后的视频到 R2 Bucket。

### 4. 依赖检查
*   **Java**: 已确认使用 `software.amazon.awssdk:s3` (AWS SDK v2)，符合 R2 官方示例要求。
*   **Python**: 已确认 `requirements.txt` 包含 `boto3`。

### 执行后需用户操作
*   在 `.env` 或 Coolify 环境变量中填入你的 Cloudflare R2 凭证 (Account ID, Access Key, Secret Key)。
