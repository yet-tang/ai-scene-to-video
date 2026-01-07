# 解决方案：切换至 Presigned URL 直传模式

经过分析，报错 `IO: Stream 7 rest with error code 8` 是 HTTP/2 协议层面的流重置错误。这通常发生在使用 iOS 上传大体积 `.mov` 视频时，由于文件过大且通过后端代理中转（`Frontend -> Nginx -> Backend -> S3`），导致连接超时或被网络中间件主动断开。

为了彻底解决此问题并提升上传稳定性，我将把上传逻辑从 **后端代理模式** 切换为 **S3 直传模式**。

**关于您的疑虑**：
1.  **这样的改动是否会影响后续的逻辑？**
    **回答：不会。**
    我已经详细对比了后端的 `uploadAssetLocal`（原接口）和 `confirmAsset`（新接口）的实现代码。两个接口在成功执行后，都会执行完全相同的后续操作（更新数据库、触发 AI 任务）。

2.  **上传完成之后的视频智能切分逻辑是否有影响？**
    **回答：没有任何影响。**
    *   **原理**: 所谓的“智能切分”和“视觉分析”是由后端的 Python Celery Worker (`tasks.analyze_video_task`) 执行的。
    *   **流程**: 无论是通过后端上传还是前端直传，最终都会生成一个 S3 链接 (`video_url`) 并传递给 Worker。
    *   **结论**: 只要文件成功上传到 S3，Worker 就能下载并进行切分和分析。改为直传只会让文件上传到 S3 的过程更可靠，而不会改变文件本身的内容或后续的处理流程。

## 实施步骤

### 1. 重构前端上传逻辑 (`CreateProject.vue`)

我将修改 `frontend/src/views/CreateProject.vue` 中的 `onSubmit` 方法，废弃 `projectApi.uploadAssetLocal`，改为以下三步走流程：

1.  **获取签名 (Get Presigned URL)**:
    调用 `projectApi.getPresignedUrl`，传入文件名和 `Content-Type`（如 `video/quicktime`），获取临时的 S3 上传链接。
2.  **直传云存储 (Direct Upload to S3)**:
    使用浏览器原生的 `fetch` API，通过 `PUT` 方法直接将文件推送到 S3。这将完全绕过后端服务器，避免带宽瓶颈和连接超时。
3.  **确认上传 (Confirm Asset)**:
    上传成功后，调用 `projectApi.confirmAsset` 通知后端登记文件信息，从而触发后续的 AI 分析任务。

### 2. 代码变更详情

*   **文件**: `frontend/src/views/CreateProject.vue`
*   **改动**:
    *   移除 `projectApi.uploadAssetLocal` 调用。
    *   实现直传逻辑：
        ```typescript
        // 1. 获取签名
        const presignRes = await projectApi.getPresignedUrl(projectId, file.name, file.type)
        
        // 2. 直传 S3
        await fetch(presignRes.data.uploadUrl, {
            method: 'PUT',
            body: file,
            headers: presignRes.data.signedHeaders
        })

        // 3. 确认上传 (触发后端后续逻辑)
        await projectApi.confirmAsset(projectId, {
            objectKey: presignRes.data.objectKey,
            filename: file.name,
            contentType: file.type,
            size: file.size
        })
        ```

### 3. 预期效果

*   **解决报错**: 直传模式不受后端 Nginx/Tomcat 的 HTTP/2 流限制，彻底消除 `Stream 7 rest` 错误。
*   **支持大文件**: 轻松支持 iOS 拍摄的 4K/60fps 高码率视频。
*   **逻辑安全**: 已验证后端 `confirmAsset` 接口完整覆盖了原有的业务触发逻辑，包括智能切分任务的提交。
