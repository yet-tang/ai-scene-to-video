# 可观测性与运维规则 (Observability & Ops Rules)

## 1. 全链路追踪 (Tracing)
- **Request ID**:
  - **接收**: 所有 HTTP 接口必须读取 `X-Request-Id`。
  - **透传**: 调用下游服务（如 Worker, 外部 API）时必须携带此 ID。
  - **响应**: HTTP Response Header 必须包含 `X-Request-Id`。
- **日志关联**: Logback/MDC 配置必须包含 `request_id` 字段。

## 2. 健康检查 (Health Checks)
- **/health**: 
  - 逻辑: 仅检查进程是否存活。
  - 响应: `200 OK` (无 Body 或简单 JSON)。
- **/ready**:
  - 逻辑: 检查 DB、Redis、S3 连接池是否可用。
  - 响应: `200 OK` (可用) / `503 Service Unavailable` (不可用)。

## 3. 日志规范 (Logging)
- **格式**: 生产环境必须输出 JSON 格式日志。
- **必填字段**:
  - `level`: INFO/WARN/ERROR
  - `timestamp`: ISO-8601
  - `service`: `ai-scene-backend` / `ai-scene-engine`
  - `trace_id`: 即 request_id
  - `message`: 人类可读信息
- **禁止**: 禁止打印密码、密钥、用户 Token。

## 4. 变更管理 (GitOps)
- **路由变更**: 修改 `router-service/routes.yaml` 并提交 PR。
- **鉴权变更**: 修改 `auth-service/src/config.yaml` 并提交 PR。
- **验收**: 必须提供测试环境的 `X-Request-Id` 以证明变更有效且无副作用。
