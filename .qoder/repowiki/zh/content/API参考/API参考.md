# API参考

<cite>
**本文档中引用的文件**   
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java)
- [HealthController.java](file://backend/src/main/java/com/aiscene/controller/HealthController.java)
- [CreateProjectRequest.java](file://backend/src/main/java/com/aiscene/dto/CreateProjectRequest.java)
- [ProjectListItemResponse.java](file://backend/src/main/java/com/aiscene/dto/ProjectListItemResponse.java)
- [TimelineResponse.java](file://backend/src/main/java/com/aiscene/dto/TimelineResponse.java)
- [PresignedUrlResponse.java](file://backend/src/main/java/com/aiscene/dto/PresignedUrlResponse.java)
- [AssetConfirmRequest.java](file://backend/src/main/java/com/aiscene/dto/AssetConfirmRequest.java)
- [UpdateAssetRequest.java](file://backend/src/main/java/com/aiscene/dto/UpdateAssetRequest.java)
- [Project.java](file://backend/src/main/java/com/aiscene/entity/Project.java)
- [ProjectStatus.java](file://backend/src/main/java/com/aiscene/entity/ProjectStatus.java)
- [application.yml](file://backend/src/main/resources/application.yml)
- [client.ts](file://frontend/src/api/client.ts)
- [GATEWAY_CORS_GUIDE.md](file://docs/GATEWAY_CORS_GUIDE.md)
</cite>

## 目录
1. [简介](#简介)
2. [API基础信息](#api基础信息)
3. [认证机制](#认证机制)
4. [项目管理API](#项目管理api)
5. [健康检查端点](#健康检查端点)
6. [错误码](#错误码)
7. [数据模型](#数据模型)

## 简介
本文档为ai-scene-to-video后端服务提供的RESTful API提供了详尽的技术参考。文档详细描述了`ProjectController.java`中定义的所有端点，包括HTTP方法、URL路径、请求头、请求体和响应体的规范。同时，文档也包含了`HealthController.java`提供的健康检查端点信息。本参考文档旨在为前端开发者和第三方集成者提供调用API所需的所有技术细节。

## API基础信息
- **基础URL**: `http://<host>:8090/v1/projects`
- **协议**: HTTP/HTTPS
- **内容类型**: `application/json`
- **服务器端口**: 8090 (由`application.yml`配置)

**Section sources**
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L29)
- [application.yml](file://backend/src/main/resources/application.yml#L2)

## 认证机制
API使用基于API Key的认证机制。客户端需要在HTTP请求头中包含`Authorization`字段。

- **请求头**: `Authorization: ApiKey <your-api-key>`
- **示例**: `Authorization: ApiKey abc123-def456-ghi789`

前端代码示例（来自`client.ts`）：
```typescript
config.headers['Authorization'] = `ApiKey ${apiKey}`
```

**Section sources**
- [client.ts](file://frontend/src/api/client.ts#L16)
- [GATEWAY_CORS_GUIDE.md](file://docs/GATEWAY_CORS_GUIDE.md#L1)

## 项目管理API

### 获取项目列表
获取用户的所有项目，支持分页。

**HTTP方法**: `GET`  
**URL路径**: `/`  
**请求头**:  
- `X-User-Id` (可选): 用户ID，用于过滤特定用户的项目

**请求参数**:  
- `page` (可选): 页码，默认为1
- `size` (可选): 每页大小，默认为10

**成功响应 (200)**:  
```json
{
  "content": [
    {
      "id": "uuid",
      "title": "string",
      "status": "DRAFT|UPLOADING|ANALYZING|REVIEW|SCRIPT_GENERATING|SCRIPT_GENERATED|AUDIO_GENERATING|AUDIO_GENERATED|RENDERING|COMPLETED|FAILED",
      "houseInfo": {},
      "createdAt": "2023-01-01T00:00:00",
      "errorRequestId": "string",
      "errorStep": "string",
      "errorAt": "2023-01-01T00:00:00"
    }
  ],
  "totalElements": 0,
  "totalPages": 0,
  "size": 0,
  "number": 0
}
```

**Section sources**
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L42-L58)

### 创建项目
创建一个新的项目。

**HTTP方法**: `POST`  
**URL路径**: `/`  
**请求体**: `CreateProjectRequest` 对象

**请求体 (CreateProjectRequest)**:
```json
{
  "userId": 0,
  "title": "string",
  "houseInfo": {}
}
```

**成功响应 (200)**:  
返回完整的`Project`对象。

**Section sources**
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L61-L65)
- [CreateProjectRequest.java](file://backend/src/main/java/com/aiscene/dto/CreateProjectRequest.java#L7-L12)
- [Project.java](file://backend/src/main/java/com/aiscene/entity/Project.java#L17-L72)

### 获取项目详情
根据项目ID获取项目的详细信息。

**HTTP方法**: `GET`  
**URL路径**: `/{id}`  
**路径参数**:  
- `id`: 项目UUID

**成功响应 (200)**:  
返回完整的`Project`对象。

**Section sources**
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L67-L71)

### 获取预签名URL
为上传文件生成一个预签名的URL。

**HTTP方法**: `POST`  
**URL路径**: `/{id}/assets/presign`  
**路径参数**:  
- `id`: 项目UUID

**查询参数**:  
- `filename`: 文件名
- `contentType`: 内容类型 (如 `video/mp4`)

**成功响应 (200)**:  
```json
{
  "uploadUrl": "string",
  "publicUrl": "string",
  "objectKey": "string",
  "signedHeaders": {}
}
```

**Section sources**
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L73-L82)
- [PresignedUrlResponse.java](file://backend/src/main/java/com/aiscene/dto/PresignedUrlResponse.java#L7-L14)

### 确认资产
确认一个已上传的资产。

**HTTP方法**: `POST`  
**URL路径**: `/{id}/assets/confirm`  
**路径参数**:  
- `id`: 项目UUID

**请求体 (AssetConfirmRequest)**:
```json
{
  "objectKey": "string",
  "filename": "string",
  "contentType": "string",
  "size": 0
}
```

**成功响应 (200)**:  
返回`Asset`对象。

**Section sources**
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L84-L89)
- [AssetConfirmRequest.java](file://backend/src/main/java/com/aiscene/dto/AssetConfirmRequest.java#L7-L12)

### 上传资产
通过文件上传的方式上传一个资产。

**HTTP方法**: `POST`  
**URL路径**: `/{id}/assets`  
**路径参数**:  
- `id`: 项目UUID

**请求参数**:  
- `file`: MultipartFile

**成功响应 (200)**:  
返回`Asset`对象。

**Section sources**
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L91-L96)

### 本地上传资产
通过文件上传的方式上传一个资产（本地模式）。

**HTTP方法**: `POST`  
**URL路径**: `/{id}/assets/local`  
**路径参数**:  
- `id`: 项目UUID

**请求参数**:  
- `file`: MultipartFile

**成功响应 (200)**:  
返回`Asset`对象。

**Section sources**
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L98-L103)

### 更新资产
更新资产的元数据。

**HTTP方法**: `PUT`  
**URL路径**: `/{projectId}/assets/{assetId}`  
**路径参数**:  
- `projectId`: 项目UUID
- `assetId`: 资产UUID

**请求体 (UpdateAssetRequest)**:
```json
{
  "userLabel": "string",
  "sortOrder": 0
}
```

**成功响应 (200)**:  
返回`Asset`对象。

**Section sources**
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L133-L137)
- [UpdateAssetRequest.java](file://backend/src/main/java/com/aiscene/dto/UpdateAssetRequest.java#L8-L15)

### 获取时间线
获取项目的时间线信息。

**HTTP方法**: `GET`  
**URL路径**: `/{id}/timeline`  
**路径参数**:  
- `id`: 项目UUID

**成功响应 (200)**:  
```json
{
  "projectId": "string",
  "projectTitle": "string",
  "status": "DRAFT|UPLOADING|ANALYZING|REVIEW|SCRIPT_GENERATING|SCRIPT_GENERATED|AUDIO_GENERATING|AUDIO_GENERATED|RENDERING|COMPLETED|FAILED",
  "errorRequestId": "string",
  "errorStep": "string",
  "assets": [
    {}
  ],
  "scriptContent": "string"
}
```

**Section sources**
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L139-L143)
- [TimelineResponse.java](file://backend/src/main/java/com/aiscene/dto/TimelineResponse.java#L10-L21)

### 获取脚本
获取项目的脚本内容。

**HTTP方法**: `GET`  
**URL路径**: `/{id}/script`  
**路径参数**:  
- `id`: 项目UUID

**成功响应 (200)**:  
```json
{
  "projectId": "string",
  "status": "string",
  "scriptContent": "string"
}
```

**Section sources**
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L145-L153)

### 生成脚本
触发脚本生成任务。

**HTTP方法**: `POST`  
**URL路径**: `/{id}/script`  
**路径参数**:  
- `id`: 项目UUID

**成功响应 (202)**:  
```json
{
  "projectId": "string",
  "taskId": "string",
  "status": "string",
  "scriptContent": "string"
}
```

**Section sources**
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L155-L165)

### 更新脚本
更新项目的脚本内容。

**HTTP方法**: `PUT`  
**URL路径**: `/{id}/script`  
**请求头**:  
- `Content-Type: text/plain`
- `X-User-Id` (可选): 用户ID

**路径参数**:  
- `id`: 项目UUID

**请求体**: 脚本内容文本

**成功响应 (202)**: 无内容

**Section sources**
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L167-L177)

### 生成音频
触发音频生成任务。

**HTTP方法**: `POST`  
**URL路径**: `/{id}/audio`  
**路径参数**:  
- `id`: 项目UUID

**请求体 (可选)**: 脚本内容

**成功响应 (202)**: 无内容

**Section sources**
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L179-L187)

### 渲染视频
触发视频渲染任务。

**HTTP方法**: `POST`  
**URL路径**: `/{id}/render`  
**路径参数**:  
- `id`: 项目UUID

**请求头**:  
- `X-User-Id` (可选): 用户ID

**成功响应 (202)**: 无内容

**Section sources**
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L189-L195)

### 重置数据 (开发环境)
重置所有数据（仅在开发环境启用）。

**HTTP方法**: `POST`  
**URL路径**: `/dev/reset`  

**成功响应 (204)**: 无内容

**Section sources**
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L197-L204)

## 健康检查端点

### 健康检查
检查服务是否正在运行。

**HTTP方法**: `GET`  
**URL路径**: `/health`  
**成功响应 (200)**: `OK`

### 就绪检查
检查服务是否准备好接收流量（包括数据库连接）。

**HTTP方法**: `GET`  
**URL路径**: `/ready`  
**成功响应 (200)**: `OK`  
**失败响应 (503)**: `Service Unavailable: DB Connection Failed`

**Section sources**
- [HealthController.java](file://backend/src/main/java/com/aiscene/controller/HealthController.java#L21-L37)

## 错误码
| 状态码 | 含义 | 说明 |
| :--- | :--- | :--- |
| 400 | Bad Request | 请求格式错误，例如缺少必需的参数或Content-Type不支持 |
| 401 | Unauthorized | 未提供有效的API Key进行认证 |
| 403 | Forbidden | 用户无权访问该资源 |
| 404 | Not Found | 请求的资源不存在 |
| 409 | Conflict | 请求与当前状态冲突，例如尝试在错误状态下执行操作 |
| 500 | Internal Server Error | 服务器内部错误 |
| 503 | Service Unavailable | 服务不可用，例如数据库连接失败 |

**Section sources**
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L108)
- [HealthController.java](file://backend/src/main/java/com/aiscene/controller/HealthController.java#L36)

## 数据模型

### 项目状态 (ProjectStatus)
枚举类型，表示项目的当前状态。

```java
public enum ProjectStatus {
    DRAFT,
    UPLOADING,
    ANALYZING,
    REVIEW,
    SCRIPT_GENERATING,
    SCRIPT_GENERATED,
    AUDIO_GENERATING,
    AUDIO_GENERATED,
    RENDERING,
    COMPLETED,
    FAILED
}
```

**Section sources**
- [ProjectStatus.java](file://backend/src/main/java/com/aiscene/entity/ProjectStatus.java#L3-L15)

### 项目 (Project)
核心实体，代表一个视频生成项目。

**属性**:
- `id`: UUID - 项目唯一标识
- `userId`: Long - 用户ID
- `title`: String - 项目标题
- `houseInfo`: JsonNode - 房屋信息（JSON格式）
- `status`: ProjectStatus - 项目状态
- `scriptContent`: String - 脚本内容
- `audioUrl`: String - 生成的音频URL
- `finalVideoUrl`: String - 最终视频URL
- `errorLog`: String - 错误日志
- `errorTaskId`: String - 错误任务ID
- `errorRequestId`: String - 错误请求ID
- `errorStep`: String - 错误步骤
- `errorAt`: LocalDateTime - 错误发生时间
- `createdAt`: LocalDateTime - 创建时间

**Section sources**
- [Project.java](file://backend/src/main/java/com/aiscene/entity/Project.java#L17-L72)

### 创建项目请求 (CreateProjectRequest)
用于创建新项目的请求数据传输对象。

**属性**:
- `userId`: Long - 用户ID
- `title`: String - 项目标题
- `houseInfo`: Map<String, Object> - 房屋信息

**Section sources**
- [CreateProjectRequest.java](file://backend/src/main/java/com/aiscene/dto/CreateProjectRequest.java#L7-L12)

### 项目列表项响应 (ProjectListItemResponse)
用于项目列表接口的响应数据传输对象。

**属性**:
- `id`: UUID - 项目ID
- `title`: String - 项目标题
- `status`: ProjectStatus - 项目状态
- `houseInfo`: JsonNode - 房屋信息
- `createdAt`: LocalDateTime - 创建时间
- `errorRequestId`: String - 错误请求ID
- `errorStep`: String - 错误步骤
- `errorAt`: LocalDateTime - 错误发生时间

**Section sources**
- [ProjectListItemResponse.java](file://backend/src/main/java/com/aiscene/dto/ProjectListItemResponse.java#L13-L26)

### 时间线响应 (TimelineResponse)
用于获取项目时间线的响应数据传输对象。

**属性**:
- `projectId`: String - 项目ID
- `projectTitle`: String - 项目标题
- `status`: ProjectStatus - 项目状态
- `errorRequestId`: String - 错误请求ID
- `errorStep`: String - 错误步骤
- `assets`: List<Asset> - 资产列表
- `scriptContent`: String - 脚本内容

**Section sources**
- [TimelineResponse.java](file://backend/src/main/java/com/aiscene/dto/TimelineResponse.java#L10-L21)

### 预签名URL响应 (PresignedUrlResponse)
用于返回预签名URL的响应数据传输对象。

**属性**:
- `uploadUrl`: String - 上传URL
- `publicUrl`: String - 公共访问URL
- `objectKey`: String - 对象键
- `signedHeaders`: Map<String, String> - 签名头

**Section sources**
- [PresignedUrlResponse.java](file://backend/src/main/java/com/aiscene/dto/PresignedUrlResponse.java#L7-L14)

### 资产确认请求 (AssetConfirmRequest)
用于确认已上传资产的请求数据传输对象。

**属性**:
- `objectKey`: String - 对象键
- `filename`: String - 文件名
- `contentType`: String - 内容类型
- `size`: Long - 文件大小

**Section sources**
- [AssetConfirmRequest.java](file://backend/src/main/java/com/aiscene/dto/AssetConfirmRequest.java#L7-L12)

### 更新资产请求 (UpdateAssetRequest)
用于更新资产信息的请求数据传输对象。

**属性**:
- `userLabel`: String - 用户标签
- `sortOrder`: Integer - 排序顺序

**Section sources**
- [UpdateAssetRequest.java](file://backend/src/main/java/com/aiscene/dto/UpdateAssetRequest.java#L8-L15)