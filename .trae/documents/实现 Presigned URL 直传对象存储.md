# Presigned URL 直传对象存储改造计划 (最终确认版)

## 💡 技术选型答疑：为什么不直接在前端使用 AWS SDK？
用户提问关于“前端直接接入 aws-sdk-js-v3”的可行性，以下是采用 **Presigned URL 方案** 而非 **前端 SDK 方案** 的核心理由：
1.  **安全风险 (Security)**: AWS SDK 需要 AccessKey/SecretKey 才能工作。如果直接在前端集成，必须将密钥硬编码或通过网络传输，这会导致**密钥 100% 泄露**，黑客可借此控制整个存储桶。
2.  **包体积 (Bundle Size)**: AWS SDK 体积较大，仅为了上传功能引入完整 SDK 会显著增加前端构建体积，影响首屏加载速度。
3.  **架构规范**: 遵循项目现有规则“零信任”和“环境隔离”，密钥必须仅存在于后端服务器或环境变量中。

**结论**: 采用“后端生成临时签名 URL (Presigned URL) -> 前端通过标准 HTTP PUT 上传”的方案，是兼顾安全、性能和轻量化的行业最佳实践。

---

## 1. 后端改造 (Backend)

### 1.1 配置与依赖 (`S3StorageConfig.java`)
- **S3Presigner**: 配置 `S3Presigner` Bean，复用现有的 `region`, `endpoint`, `credentials`。
- **R2 兼容性**: 强制开启 `forcePathStyle(true)`，设置 `signatureDuration` (如 20分钟)。

### 1.2 服务层 (`StorageService.java`)
- **生成签名**: 实现 `generatePresignedUrl(key, contentType)`，返回签名的上传 URL。
- **安全校验**: 在生成签名时绑定 `Content-Type`，防止文件类型篡改。

### 1.3 接口层 (`ProjectController.java`)
- **Step 1: 获取上传链接** (`POST .../presign`)
    - 返回: `uploadUrl` (带签名的 PUT 地址), `publicUrl` (最终访问地址), `objectKey`, `signedHeaders`。
- **Step 2: 确认上传完成** (`POST .../confirm`)
    - 接收前端上传成功的信号，执行“保存 Asset”和“触发 AI 分析”的逻辑。

## 2. 前端改造 (Frontend)

### 2.1 上传逻辑 (`CreateProject.vue`)
- **移除 Form Data**: 不再将文件传给后端。
- **直传流程**:
    1.  调用 `getPresignedUrl` 获取上传地址。
    2.  使用 `axios.put(uploadUrl, file)` 直接上传到 S3/R2。
    3.  **关键**: 必须设置 Header `Content-Type: file.type`，需与后端签名时一致。
- **进度监控**: 使用 `axios` 的 `onUploadProgress` 更新 UI 进度条。

### 2.2 API 封装 (`api/project.ts`)
- 新增 `presign` 和 `confirm` 接口方法。

## 3. 验证计划
- **安全验证**: 尝试使用错误的 Content-Type 上传，应被 S3 拒绝 (403 SignatureDoesNotMatch)。
- **流程验证**: 完整跑通“创建项目 -> 获取链接 -> 直传 S3 -> 确认 -> 触发分析”流程。
