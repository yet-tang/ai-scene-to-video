# 网关 CORS 与鉴权配置指南

## 问题诊断
在使用 API 网关（如 Nginx, Kong, Cloudflare 等）时，常见的 CORS 失败原因为：
**网关拦截了浏览器的预检请求 (OPTIONS request) 并尝试对其进行鉴权。**

### 现象
1. 浏览器控制台报错：`Access to XMLHttpRequest ... has been blocked by CORS policy`。
2. 网络请求详情中，`OPTIONS` 请求的状态码为 **401 Unauthorized**。
3. 请求头中缺少 `Authorization` 或 API Key 字段（这是浏览器的标准安全行为，OPTIONS 请求默认不携带凭证）。

## 解决方案

你需要修改 **网关 (gw.tnight.xyz)** 的配置，使其对 `OPTIONS` 请求**跳过鉴权**并直接返回 CORS 响应头。

### Nginx 配置示例

如果在 Nginx 层面处理 CORS，请参考以下配置：

```nginx
server {
    server_name gw.tnight.xyz;

    location /api/ai-video/ {
        # 1. 允许跨域的域名 (建议指定具体域名而非 *)
        if ($http_origin ~* (https://tnight\.xyz|http://localhost:.*)) {
            add_header 'Access-Control-Allow-Origin' "$http_origin" always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE, PATCH' always;
            add_header 'Access-Control-Allow-Headers' 'Authorization,Content-Type,Accept,Origin,User-Agent,DNT,Cache-Control,X-Mx-ReqToken,Keep-Alive,X-Requested-With,If-Modified-Since' always;
            add_header 'Access-Control-Allow-Credentials' 'true' always;
        }

        # 2. 关键：对 OPTIONS 请求直接返回 204，且不执行后续的鉴权逻辑
        if ($request_method = 'OPTIONS') {
            # 再次添加 Header，因为 if 块内会重置 add_header 指令
            add_header 'Access-Control-Allow-Origin' "$http_origin" always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE, PATCH' always;
            add_header 'Access-Control-Allow-Headers' 'Authorization,Content-Type,Accept,Origin,User-Agent,DNT,Cache-Control,X-Mx-ReqToken,Keep-Alive,X-Requested-With,If-Modified-Since' always;
            add_header 'Access-Control-Allow-Credentials' 'true' always;
            
            add_header 'Content-Type' 'text/plain charset=UTF-8';
            add_header 'Content-Length' 0;
            return 204;
        }

        # 3. 正常的业务请求代理 (此处才会进行鉴权)
        # auth_request /auth; # 假设有鉴权配置
        proxy_pass http://backend_upstream;
    }
}
```

### 关键点检查
1. **顺序很重要**：OPTIONS 的处理必须在鉴权指令（如 `auth_basic`, `auth_request` 或 API 网关的插件执行）**之前**。
2. **Header 完整性**：`Access-Control-Allow-Headers` 必须包含前端发送的所有 Header，特别是 `Authorization`。

## 413 Request Entity Too Large（上传视频失败）
当你通过网关上传视频（`multipart/form-data`）时，如果遇到 `413 Request Entity Too Large`，通常有两类原因：

### 1) Cloudflare 侧限制（最常见）
如果响应头里出现 `Server: cloudflare`，并且响应体里显示 `nginx/...`，大概率是 Cloudflare 在边缘直接拦截了过大的请求体。

处理方式：
- 将上传接口使用 **DNS only**（灰云）绕过 Cloudflare 代理；或为上传单独使用不经过 Cloudflare 的域名
- 或改为 **Presigned URL 直传对象存储**（推荐，符合大文件上传最佳实践）

### 2) 你的网关 Nginx 限制
如果 413 来自你自建的 Nginx，需要在对应的 `server` 或 `location` 增加上传大小限制：

```nginx
client_max_body_size 600m;
```

并建议配合增加超时与缓冲策略（避免大文件上传中断）：
```nginx
proxy_read_timeout 600s;
proxy_send_timeout 600s;
send_timeout 600s;
```

### 推荐方案：Presigned URL 直传
对于 >10MB 的文件，优先让前端先向后端/网关请求一个 presigned URL，然后直接把文件上传到对象存储，再调用后端登记素材信息。
