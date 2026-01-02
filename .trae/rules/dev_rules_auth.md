# 鉴权与安全规则 (Auth & Security Rules)

## 1. 鉴权模型 (Authentication)
- **零信任**: 业务服务 (`backend`) 默认不信任任何请求，除非包含合法的网关头。
- **信任源头**: 仅信任以下 HTTP Header（由网关校验并注入）：
  - `X-User-Id`: 经过验证的用户 ID。
  - `X-User-Role`: 用户的 RBAC 角色。
  - `X-Internal-Auth`: 服务间调用的共享密钥（用于 Worker 回调）。

## 2. 授权规范 (Authorization)
- **Scope 命名**: `<app>.<resource>.<action>`
  - 正例: `ai-video.project.create`
  - 反例: `create_project`
- **默认拒绝**: 所有 API 接口默认需要鉴权，除了显式白名单。
- **白名单**: 仅 `/.well-known/*`, `/health`, `/ready` 允许免鉴权。

## 3. 数据安全
- **敏感字段**: 用户的手机号、邮箱等 PII 信息在落库前必须脱敏或加密。
- **Presigned URL**: 生成的 S3 临时链接有效期不得超过 1 小时。
