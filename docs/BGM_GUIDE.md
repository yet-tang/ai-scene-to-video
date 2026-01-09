# BGM 配置指南

本项目支持内置 BGM 列表，创建项目时会自动随机选择一首背景音乐。

## 快速开始

### 1. 使用 Suno AI 生成 BGM

访问 [Suno AI](https://suno.com) 并使用以下提示词生成音乐：

```
温馨生活房产视频 BGM：

风格：轻音乐 (Light Music)、氛围音乐 (Ambient)
情绪：温馨 (Cozy)、希望 (Hopeful)、平静 (Peaceful)
乐器：钢琴主旋律、轻柔的弦乐、温暖的原声吉他
节奏：慢速 70-90 BPM
时长：2-3 分钟循环版本

关键词：warm piano, soft strings, acoustic guitar, cozy home, real estate background music, gentle melody, hopeful atmosphere
```

### 2. 上传 BGM 到 S3

```bash
# 使用项目提供的上传脚本
./scripts/upload_bgm.sh warm-piano-01.mp3 cozy-acoustic-02.mp3 modern-minimal-03.mp3

# 或手动上传
aws s3 cp bgm.mp3 s3://ai-scene-assets/bgm/ \
  --endpoint-url=https://your-account.r2.cloudflarestorage.com \
  --content-type="audio/mpeg" \
  --acl public-read
```

### 3. 配置 BGM 列表

#### 本地开发 (application.yml)

编辑 `backend/src/main/resources/application.yml`:

```yaml
app:
  bgm:
    auto-select: true
    builtin-urls:
      - https://your-cdn.com/bgm/warm-piano-01.mp3
      - https://your-cdn.com/bgm/cozy-acoustic-02.mp3
      - https://your-cdn.com/bgm/modern-minimal-03.mp3
```

#### Coolify 部署

在 Coolify 控制台添加环境变量：

**变量名**: `APP_BGM_BUILTIN_URLS`

**值** (YAML 格式):
```yaml
- https://your-cdn.com/bgm/warm-piano-01.mp3
- https://your-cdn.com/bgm/cozy-acoustic-02.mp3
- https://your-cdn.com/bgm/modern-minimal-03.mp3
```

### 4. 重启服务

```bash
# Docker Compose
docker compose restart ai-scene-backend

# Coolify
# 在控制台点击 "Restart"
```

## 工作原理

1. **创建项目时**: 系统自动从 BGM 列表中随机选择一首，保存到 `projects.bgm_url`
2. **渲染视频时**: Engine 下载该 BGM 并与 TTS 混音
3. **音量控制**: BGM 默认降至 15% 音量 (`BGM_VOLUME=0.15`)
4. **Auto-ducking**: 如果启用，人声期间 BGM 自动降至 30%

## 禁用自动选择

```bash
# 在 .env 或 Coolify 中设置
APP_BGM_AUTO_SELECT=false
```

禁用后项目创建时不会自动分配 BGM。

## BGM 规范

### 文件格式
- **推荐**: MP3 (192kbps 或 320kbps)
- **时长**: 2-3 分钟（支持自动循环）
- **音量**: -18dB 到 -12dB

### 命名规范
```
风格-乐器-序号.mp3

示例：
warm-piano-01.mp3
cozy-acoustic-02.mp3
modern-minimal-03.mp3
```

## 推荐 BGM 风格

| 风格 | 适用场景 | Suno 关键词 |
|------|----------|-------------|
| 温馨钢琴 | 通用、家庭房 | warm piano, cozy, gentle melody |
| 舒适原声 | 自然采光 | acoustic guitar, airy, natural light |
| 现代极简 | 轻奢公寓 | minimalist, modern classical, elegant |
| 优雅弦乐 | 高端住宅 | strings, sophisticated, luxury |
| 阳光治愈 | 江景房、阳台 | healing music, sunny, hopeful |

## 故障排查

### BGM 未自动选择
1. 检查 `APP_BGM_AUTO_SELECT=true`
2. 检查 `application.yml` 中 `builtin-urls` 是否配置
3. 查看日志确认 BGM 列表已加载

### BGM 下载失败
1. 测试 URL 可访问性：`curl -I <bgm_url>`
2. 检查 S3 Bucket 权限（必须公开可读）
3. 验证 CDN 配置

### BGM 音量问题
```bash
# 调整 BGM 音量
BGM_VOLUME=0.10  # 范围 0.05-0.30，默认 0.15
```

## 版权说明

- ✅ Suno AI 生成的音乐自动获得商用授权
- ✅ 使用无版权音乐库（如 Pixabay, FreePD）
- ❌ 禁止使用未授权的商业音乐
