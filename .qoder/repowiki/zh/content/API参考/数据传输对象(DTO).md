# 数据传输对象(DTO)

<cite>
**本文档中引用的文件**   
- [CreateProjectRequest.java](file://backend/src/main/java/com/aiscene/dto/CreateProjectRequest.java)
- [ProjectListItemResponse.java](file://backend/src/main/java/com/aiscene/dto/ProjectListItemResponse.java)
- [AssetConfirmRequest.java](file://backend/src/main/java/com/aiscene/dto/AssetConfirmRequest.java)
- [PresignedUrlResponse.java](file://backend/src/main/java/com/aiscene/dto/PresignedUrlResponse.java)
- [TimelineResponse.java](file://backend/src/main/java/com/aiscene/dto/TimelineResponse.java)
- [UpdateAssetRequest.java](file://backend/src/main/java/com/aiscene/dto/UpdateAssetRequest.java)
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java)
- [ProjectService.java](file://backend/src/main/java/com/aiscene/service/ProjectService.java)
- [ProjectStatus.java](file://backend/src/main/java/com/aiscene/entity/ProjectStatus.java)
- [Asset.java](file://backend/src/main/java/com/aiscene/entity/Asset.java)
</cite>

## 目录
1. [简介](#简介)
2. [CreateProjectRequest](#createprojectrequest)
3. [ProjectListItemResponse](#projectlistitemresponse)
4. [AssetConfirmRequest](#assetconfirmrequest)
5. [PresignedUrlResponse](#presignedurlresponse)
6. [TimelineResponse](#timelineresponse)
7. [UpdateAssetRequest](#updateassetrequest)

## 简介
本文档详细描述了AI场景到视频生成系统中所有API使用的数据传输对象（DTO）。这些DTO用于在前端和后端之间传递数据，涵盖了项目创建、资产确认、预签名URL生成、时间线获取和资产更新等核心功能。每个DTO都包含了特定的字段，用于满足不同API请求和响应的需求。

## CreateProjectRequest

`CreateProjectRequest` DTO用于创建新项目，包含项目的基本信息和房屋信息。该对象通过POST请求发送到`/v1/projects`端点，由`ProjectController.createProject()`方法处理，并传递给`ProjectService.createProject()`服务方法。

**字段说明**：
- `userId`: 用户ID，标识创建项目的用户
- `title`: 项目标题，必填字段，用于标识项目名称
- `houseInfo`: 房屋信息，以键值对形式存储房间、厅、面积、价格等信息

**JSON序列化示例**：
```json
{
  "userId": 123,
  "title": "温馨两居室",
  "houseInfo": {
    "room": 2,
    "hall": 1,
    "area": 85,
    "price": 3500000
  }
}
```

**使用场景**：当用户在前端界面点击创建新项目时，前端会收集项目标题和房屋信息，然后构造`CreateProjectRequest`对象并发送HTTP POST请求到后端。后端服务将这些信息保存到数据库中，创建一个状态为"DRAFT"的新项目。

**Section sources**
- [CreateProjectRequest.java](file://backend/src/main/java/com/aiscene/dto/CreateProjectRequest.java#L1-L13)
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L61-L65)
- [ProjectService.java](file://backend/src/main/java/com/aiscene/service/ProjectService.java#L49-L141)

## ProjectListItemResponse

`ProjectListItemResponse` DTO用于响应项目列表查询请求，提供项目的基本信息和状态。该对象由`ProjectController.listProjects()`方法返回，通过`ProjectListItemResponse.builder()`构建器模式创建。

**字段说明**：
- `id`: 项目唯一标识符，使用UUID类型
- `title`: 项目标题
- `status`: 项目当前状态，引用`ProjectStatus`枚举类型
- `houseInfo`: 房屋信息，以`JsonNode`形式存储，便于JSON序列化
- `createdAt`: 项目创建时间，使用`LocalDateTime`类型
- `errorRequestId`: 错误请求ID，用于追踪失败的请求
- `errorStep`: 错误发生的具体步骤
- `errorAt`: 错误发生的时间

**JSON序列化示例**：
```json
{
  "id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
  "title": "现代三居室",
  "status": "ANALYZING",
  "houseInfo": {
    "room": 3,
    "hall": 2,
    "area": 120,
    "price": 5000000
  },
  "createdAt": "2024-01-15T10:30:00",
  "errorRequestId": null,
  "errorStep": null,
  "errorAt": null
}
```

**使用场景**：当用户访问项目列表页面时，前端会调用`GET /v1/projects`接口获取用户的项目列表。后端从数据库查询项目数据，并将其转换为`ProjectListItemResponse`对象列表返回给前端，用于在UI上显示项目概览信息。

**Section sources**
- [ProjectListItemResponse.java](file://backend/src/main/java/com/aiscene/dto/ProjectListItemResponse.java#L1-L27)
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L42-L58)
- [ProjectStatus.java](file://backend/src/main/java/com/aiscene/entity/ProjectStatus.java#L1-L16)

## AssetConfirmRequest

`AssetConfirmRequest` DTO用于确认已上传的资产文件，包含文件的存储信息和元数据。该对象通过POST请求发送到`/v1/projects/{id}/assets/confirm`端点，由`ProjectController.confirmAsset()`方法处理。

**字段说明**：
- `objectKey`: 对象存储中的唯一键，标识文件在S3或类似存储系统中的位置
- `filename`: 文件原始名称
- `contentType`: 文件MIME类型，用于验证文件类型
- `size`: 文件大小（字节）

**JSON序列化示例**：
```json
{
  "objectKey": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8-video.mp4",
  "filename": "living_room.mp4",
  "contentType": "video/mp4",
  "size": 52428800
}
```

**使用场景**：当用户通过前端界面上传视频文件时，系统首先生成预签名URL，用户使用该URL直接上传文件到对象存储。上传完成后，前端发送`AssetConfirmRequest`到后端确认文件已成功上传。后端验证文件类型后，创建资产记录并提交分析任务。

**Section sources**
- [AssetConfirmRequest.java](file://backend/src/main/java/com/aiscene/dto/AssetConfirmRequest.java#L1-L13)
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L84-L89)
- [ProjectService.java](file://backend/src/main/java/com/aiscene/service/ProjectService.java#L49-L84)

## PresignedUrlResponse

`PresignedUrlResponse` DTO用于响应预签名URL生成请求，提供文件上传所需的URL和相关参数。该对象由`ProjectController.getPresignedUrl()`方法返回，通过`StorageService.generatePresignedUrl()`生成。

**字段说明**：
- `uploadUrl`: 上传URL，客户端使用此URL直接上传文件到对象存储
- `publicUrl`: 公共访问URL，文件上传完成后可通过此URL访问
- `objectKey`: 对象存储中的键，标识文件的唯一位置
- `signedHeaders`: 签名头部，上传时需要包含的额外HTTP头部

**JSON序列化示例**：
```json
{
  "uploadUrl": "https://storage.example.com/bucket/a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8-video.mp4?X-Amz-Algorithm=AWS4-HMAC-SHA256&...",
  "publicUrl": "https://cdn.example.com/a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8-video.mp4",
  "objectKey": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8-video.mp4",
  "signedHeaders": {
    "Content-Type": "video/mp4"
  }
}
```

**使用场景**：当用户选择上传视频文件时，前端调用`GET /v1/projects/{id}/assets/presign`接口获取预签名URL。后端生成唯一的`objectKey`，并调用存储服务生成临时的上传URL和公共访问URL。前端使用上传URL直接将文件上传到对象存储，避免了通过后端服务器中转，提高了上传效率和可扩展性。

**Section sources**
- [PresignedUrlResponse.java](file://backend/src/main/java/com/aiscene/dto/PresignedUrlResponse.java#L1-L15)
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L73-L82)
- [ProjectService.java](file://backend/src/main/java/com/aiscene/service/ProjectService.java#L58-L74)

## TimelineResponse

`TimelineResponse` DTO用于响应时间线查询请求，提供项目的时间线信息，包括AI分析出的场景列表及其时间戳。该对象由`ProjectController.getTimeline()`方法返回，通过`ProjectService.getSmartTimeline()`方法构建。

**字段说明**：
- `projectId`: 项目ID，字符串格式
- `projectTitle`: 项目标题
- `status`: 项目当前状态
- `errorRequestId`: 错误请求ID
- `errorStep`: 错误步骤
- `assets`: 资产列表，包含每个资产的详细信息，如场景标签、持续时间等
- `scriptContent`: 脚本内容，AI生成的视频脚本

**JSON序列化示例**：
```json
{
  "projectId": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
  "projectTitle": "温馨两居室",
  "status": "ANALYZING",
  "errorRequestId": null,
  "errorStep": null,
  "assets": [
    {
      "id": "e1f2g3h4-i5j6-k7l8-m9n0-o1p2q3r4s5t6",
      "ossUrl": "https://cdn.example.com/video1.mp4",
      "duration": 30.5,
      "sceneLabel": "客厅",
      "sceneScore": 0.95,
      "userLabel": "主客厅",
      "sortOrder": 0,
      "isDeleted": false
    },
    {
      "id": "u1v2w3x4-y5z6-a7b8-c9d0-e1f2g3h4i5j6",
      "ossUrl": "https://cdn.example.com/video2.mp4",
      "duration": 25.0,
      "sceneLabel": "卧室",
      "sceneScore": 0.88,
      "userLabel": "主卧",
      "sortOrder": 1,
      "isDeleted": false
    }
  ],
  "scriptContent": "欢迎参观这套温馨的两居室..."
}
```

**使用场景**：当用户访问项目时间线页面时，前端定期调用`GET /v1/projects/{id}/timeline`接口获取最新的时间线信息。后端查询项目的所有资产，并根据AI分析结果（场景标签）对资产进行智能排序。前端使用返回的数据构建可视化时间线，让用户可以查看和编辑视频场景的顺序。

**Section sources**
- [TimelineResponse.java](file://backend/src/main/java/com/aiscene/dto/TimelineResponse.java#L1-L21)
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L139-L143)
- [ProjectService.java](file://backend/src/main/java/com/aiscene/service/ProjectService.java#L86-L124)
- [Asset.java](file://backend/src/main/java/com/aiscene/entity/Asset.java#L1-L61)

## UpdateAssetRequest

`UpdateAssetRequest` DTO用于更新资产的元数据，如用户标签和排序顺序。该对象通过PUT请求发送到`/v1/projects/{projectId}/assets/{assetId}`端点，由`ProjectController.updateAsset()`方法处理。

**字段说明**：
- `userLabel`: 用户自定义标签，用于覆盖AI自动识别的场景标签
- `sortOrder`: 排序顺序，用于确定资产在时间线中的位置

**JSON序列化示例**：
```json
{
  "userLabel": "明亮的客厅",
  "sortOrder": 2
}
```

**使用场景**：当用户在时间线界面编辑某个视频片段时，可以修改其显示名称（用户标签）和在视频中的播放顺序。前端收集用户的修改，构造`UpdateAssetRequest`对象并发送到后端。后端更新资产记录，同时将`userLabel`同步到`sceneLabel`字段，确保后续处理使用用户指定的标签。

**Section sources**
- [UpdateAssetRequest.java](file://backend/src/main/java/com/aiscene/dto/UpdateAssetRequest.java#L1-L16)
- [ProjectController.java](file://backend/src/main/java/com/aiscene/controller/ProjectController.java#L133-L137)
- [ProjectService.java](file://backend/src/main/java/com/aiscene/service/ProjectService.java#L126-L141)