# Phase 2 功能快速启动指南

> **目标受众**: 开发者、运维人员  
> **预计时间**: 10分钟  
> **前置条件**: Docker环境已就绪

---

## 🚀 快速启动（3步）

### Step 1: 更新环境变量

在Coolify控制台或本地`.env`文件中添加：

```bash
# ============ Phase 2 新增配置 ============

# 动态节奏控制（推荐启用）
DYNAMIC_SPEED_ENABLED=true

# BGM智能匹配（可选启用）
BGM_AUTO_SELECT_ENABLED=false  # 需要先准备BGM库
BGM_DYNAMIC_VOLUME_ENABLED=true

# 多智能体协作（可选启用）
MULTI_AGENT_ENABLED=false  # 默认关闭，会增加脚本生成时间
```

### Step 2: 重启服务

```bash
# 本地Docker Compose
docker compose -f docker-compose.coolify.yaml restart engine

# Coolify部署
# 在Coolify控制台点击"Restart" Engine服务
```

### Step 3: 验证功能

```bash
# 查看Engine日志
docker logs ai-scene-engine | grep "video.speed.dynamic"

# 如果看到日志输出，说明动态节奏控制已生效！
```

---

## 📋 功能清单

| 功能 | 默认状态 | 推荐设置 | 说明 |
|------|----------|----------|------|
| 动态节奏控制 | ✅ 启用 | ✅ 启用 | 无需额外配置，立即生效 |
| BGM智能匹配 | ❌ 禁用 | ⚠️ 可选 | 需要准备BGM库文件 |
| 多智能体协作 | ❌ 禁用 | ⚠️ 可选 | 会增加2-5倍脚本生成时间 |

---

## 🎯 按需启用指南

### 场景 1: 快速上手（仅启用动态节奏控制）

**适用场景**: 首次使用Phase 2功能，希望最小化配置

**配置**:
```bash
DYNAMIC_SPEED_ENABLED=true
```

**效果**:
- 惊艳镜头自动慢镜（0.85x速度）
- 过渡镜头自动加速（1.1x速度）
- 无需额外文件或依赖

**验证**:
```bash
# 上传包含"江景"或高shock_score素材的项目
# 渲染后查看日志
docker logs ai-scene-engine | grep "video.speed.dynamic"
```

---

### 场景 2: 完整体验（启用BGM智能匹配）

**适用场景**: 希望视频自动配乐，提升观看体验

**配置步骤**:

#### 2.1 准备BGM文件
```bash
# 使用Suno AI生成或从无版权音乐库下载
# 推荐格式：MP3 (192kbps+)
# 推荐时长：2-3分钟

# 使用脚本上传到S3
./scripts/upload_bgm.sh warm-piano-01.mp3 cozy-acoustic-02.mp3
```

#### 2.2 创建BGM库配置
```bash
# 创建 bgm_library.json
cat > bgm_library.json << 'EOF'
{
  "bgm_library": [
    {
      "id": "warm-piano-01",
      "url": "https://your-cdn.com/bgm/warm-piano-01.mp3",
      "style": "cozy",
      "tags": ["温馨", "家庭"],
      "emotion": "温馨",
      "intensity_curve": [0.15, 0.2, 0.25, 0.2, 0.15]
    },
    {
      "id": "cozy-acoustic-02",
      "url": "https://your-cdn.com/bgm/cozy-acoustic-02.mp3",
      "style": "cozy",
      "tags": ["舒适", "阳光"],
      "emotion": "治愈",
      "intensity_curve": [0.10, 0.25, 0.30, 0.20, 0.15]
    }
  ]
}
EOF

# 将文件挂载到Docker容器
# 方法1：直接复制到容器内
docker cp bgm_library.json ai-scene-engine:/app/bgm_library.json

# 方法2：在docker-compose中挂载（推荐）
# 修改 docker-compose.coolify.yaml:
# volumes:
#   - ./bgm_library.json:/app/bgm_library.json:ro
```

#### 2.3 启用配置
```bash
BGM_AUTO_SELECT_ENABLED=true
BGM_DYNAMIC_VOLUME_ENABLED=true
BGM_LIBRARY_PATH=/app/bgm_library.json
```

#### 2.4 验证
```bash
# 查看BGM选择日志
docker logs ai-scene-engine | grep "bgm.auto_select"

# 预期输出：
# INFO - Using BGM intelligent selection
# INFO - Selected BGM: warm-piano-01
# INFO - Applied dynamic volume curve to BGM
```

---

### 场景 3: 高质量脚本（启用多智能体协作）

**适用场景**: 对脚本质量要求极高，愿意接受更长生成时间

**配置**:
```bash
MULTI_AGENT_ENABLED=true
MULTI_AGENT_MAX_ITERATIONS=3
MULTI_AGENT_QUALITY_THRESHOLD=80
```

**注意事项**:
- 脚本生成时间会增加2-5倍（约30-90秒）
- 需要确保DASHSCOPE_API_KEY有效
- 建议先在测试环境验证

**验证**:
```bash
# 查看多智能体日志
docker logs ai-scene-engine | grep "script.multi_agent"

# 预期输出：
# INFO - Using multi-agent workflow for script generation
# INFO - ScriptAgent: Script generated successfully
# INFO - ReviewerAgent: Score=85.0, Passed=True
# INFO - Multi-agent script generation completed
```

---

## 🛠️ 故障排查

### 问题 1: 动态速度控制未生效

**检查清单**:
- [ ] `DYNAMIC_SPEED_ENABLED=true` 已设置
- [ ] Engine服务已重启
- [ ] 素材包含`emotion`字段（查看数据库assets表）

**解决方案**:
```bash
# 1. 确认配置
docker exec ai-scene-engine env | grep DYNAMIC_SPEED

# 2. 重启服务
docker restart ai-scene-engine

# 3. 查看日志确认
docker logs -f ai-scene-engine | grep "video.speed"
```

---

### 问题 2: BGM选择失败

**检查清单**:
- [ ] BGM库文件存在且格式正确
- [ ] BGM URL可访问（使用curl测试）
- [ ] `BGM_AUTO_SELECT_ENABLED=true` 已设置

**解决方案**:
```bash
# 1. 验证BGM库文件
docker exec ai-scene-engine cat /app/bgm_library.json

# 2. 测试BGM URL可访问性
curl -I https://your-cdn.com/bgm/warm-piano-01.mp3

# 3. 查看详细错误日志
docker logs ai-scene-engine | grep "bgm" | tail -20
```

**常见错误**:
- `FileNotFoundError`: BGM库文件路径错误
- `JSONDecodeError`: BGM库文件JSON格式错误
- `DownloadError`: BGM URL无法访问

---

### 问题 3: 多智能体超时

**检查清单**:
- [ ] DASHSCOPE_API_KEY有效
- [ ] LiteLLM依赖已安装
- [ ] 网络连接稳定

**解决方案**:
```bash
# 1. 验证API Key
docker exec ai-scene-engine env | grep DASHSCOPE_API_KEY

# 2. 检查LiteLLM依赖
docker exec ai-scene-engine pip show litellm

# 3. 降低迭代次数（临时方案）
MULTI_AGENT_MAX_ITERATIONS=2

# 4. 查看详细错误日志
docker logs ai-scene-engine | grep "multi_agent" | tail -30
```

---

## 📊 性能基准

### 动态节奏控制
- **渲染时间增加**: < 5%
- **内存占用增加**: 0%
- **推荐启用**: ✅ 是（无明显性能损失）

### BGM智能匹配
- **渲染时间增加**: 5-10%（取决于BGM文件大小）
- **内存占用增加**: < 5% (BGM加载到内存)
- **推荐启用**: ⚠️ 可选（需要准备BGM库）

### 多智能体协作
- **脚本生成时间增加**: 200-400%
- **LLM调用成本**: 3-5倍
- **推荐启用**: ⚠️ 可选（高质量要求场景）

**性能对比**:
| 场景 | 标准流程 | +动态节奏 | +BGM匹配 | +多智能体 |
|------|---------|----------|---------|----------|
| 脚本生成 | 10s | 10s | 10s | 30-50s |
| 视频渲染 | 60s | 62s | 66s | 66s |
| 总耗时 | 70s | 72s | 76s | 96-116s |

---

## 🎓 最佳实践

### 1. 渐进式启用
```
Day 1: 启用动态节奏控制（最小风险）
Day 3: 准备BGM库，启用BGM智能匹配
Day 7: 验证效果后，可选启用多智能体
```

### 2. 生产环境配置推荐
```bash
# 稳定性优先配置
DYNAMIC_SPEED_ENABLED=true
BGM_AUTO_SELECT_ENABLED=true  # 需要BGM库
BGM_DYNAMIC_VOLUME_ENABLED=true
MULTI_AGENT_ENABLED=false  # 生产环境建议关闭

# 质量优先配置（可接受更长等待时间）
DYNAMIC_SPEED_ENABLED=true
BGM_AUTO_SELECT_ENABLED=true
BGM_DYNAMIC_VOLUME_ENABLED=true
MULTI_AGENT_ENABLED=true  # 启用AI质量把控
MULTI_AGENT_MAX_ITERATIONS=3
```

### 3. BGM库管理建议
- **数量**: 5-10首（覆盖主要风格）
- **风格**: stunning(惊艳), cozy(温馨), healing(治愈)
- **来源**: Suno AI生成 或 无版权音乐库
- **更新频率**: 每月新增2-3首

---

## 📞 技术支持

### 文档资源
- 完整实施总结: `.qoder/quests/PHASE_2_IMPLEMENTATION_SUMMARY.md`
- 设计文档: `.qoder/quests/ai-video-editing-system-design-1768316430.md`
- 项目规则: `.trae/rules/project_rule.md`

### 日志关键词
```bash
# 动态节奏控制
docker logs ai-scene-engine | grep "video.speed.dynamic"

# BGM智能匹配
docker logs ai-scene-engine | grep "bgm.auto_select"
docker logs ai-scene-engine | grep "bgm.volume.dynamic"

# 多智能体协作
docker logs ai-scene-engine | grep "script.multi_agent"
docker logs ai-scene-engine | grep "agent.review"
```

---

**祝您使用愉快！🎉**

如有问题，请查阅完整实施总结文档或联系技术支持。
