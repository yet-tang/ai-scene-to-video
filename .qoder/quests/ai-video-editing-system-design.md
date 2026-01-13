# AI房产短视频智能剪辑系统设计优化方案

## 一、战略目标定位

基于专业探房博主的爆款视频制作经验，本设计旨在将现有的「流水线式AI视频生成系统」升级为「多智能体协作的智能剪辑系统」，核心目标：

1. **降低认知负载**：用户仅需上传原始实勘视频，系统自动完成从分析到成片的全流程
2. **提升内容质量**：通过专家级Prompt工程和多模态AI能力，生成媲美人工剪辑的爆款视频
3. **保持温情调性**：延续现有"温情生活风"，强化情感共鸣和真实感

## 二、核心架构设计

### 2.1 系统架构对比

#### 当前架构（流水线模式）
```
用户上传 → 视觉分析 → 脚本生成 → 音频合成 → 视频渲染 → 输出成片
         ↓           ↓           ↓           ↓
      单次调用    单次调用    单次调用    单次调用
```

**痛点**：
- 各环节相互独立，缺乏反馈循环
- 视觉分析浅层化，仅识别场景类型和简单特征
- 脚本生成基于固定模板，缺乏爆款逻辑
- 视频剪辑机械对齐音频，无智能节奏控制

#### 优化架构（多智能体协作模式）
```
┌─────────────────────────────────────────────────────────┐
│                   总导演Agent (Orchestrator)              │
│   职责：全局协调、质量把控、迭代优化决策                   │
└─────────────────────────────────────────────────────────┘
         │
         ├───► 视频深度分析Agent
         │       └─ 镜头切分 + 亮点评分 + 情绪标注
         │
         ├───► 卖点提炼Agent
         │       └─ 核心卖点 + 调性判断 + 钩子设计
         │
         ├───► 脚本创作Agent
         │       └─ 爆款脚本 + 节奏设计 + 真实槽点
         │
         ├───► 智能剪辑Agent
         │       └─ 动态节奏 + 转场设计 + 高光镜头前置
         │
         ├───► 音频编排Agent
         │       └─ 配音生成 + BGM匹配 + 音效插入
         │
         └───► 视觉增强Agent
                 └─ 字幕叠加 + 区域标注 + 特效点缀
```

### 2.2 统一大模型调用抽象层

**设计目标**：解耦业务逻辑与模型提供商，支持灵活切换模型而无需修改Agent代码

#### 核心需求
1. **多模型支持**：Qwen、Grok、Claude、GPT、Gemini等
2. **配置化管理**：每个Agent可独立指定模型
3. **统一接口**：屏蔽不同提供商的API差异
4. **成本控制**：支持降级策略和模型路由

#### 推荐方案：LiteLLM

**选型理由**：
- ✅ 开源且活跃维护（GitHub 8k+ stars）
- ✅ 支持100+ 模型提供商（OpenAI、Anthropic、阿里云、智谱等）
- ✅ 统一的OpenAI SDK接口，迁移成本低
- ✅ 内置重试、fallback、负载均衡
- ✅ 支持流式/非流式调用
- ✅ Python原生支持，与现有Engine无缝集成

**架构设计**：

```
┌─────────────────────────────────────────────────────────┐
│                    配置层 (config.py)                     │
│   model_mapping = {                                      │
│     "vision_agent": "qwen-vl-max",                      │
│     "selling_point_agent": "grok-beta",                │
│     "script_agent": "claude-3-7-sonnet",               │
│     "fallback": "qwen-plus"                             │
│   }                                                      │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│              抽象层 (llm_client.py)                       │
│   class UnifiedLLMClient:                                │
│     def __init__(self, agent_name: str)                 │
│     def chat(messages, **kwargs) → Response             │
│     def multimodal(content, **kwargs) → Response        │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│              LiteLLM 层                                   │
│   litellm.completion(                                    │
│     model="grok-beta",                                   │
│     messages=[...],                                      │
│     api_base="https://api.x.ai/v1",                     │
│     api_key=os.getenv("GROK_API_KEY")                   │
│   )                                                      │
└─────────────────────────────────────────────────────────┘
         │
         ├────► Qwen (DashScope API)
         ├────► Grok (X.AI API)
         ├────► Claude (Anthropic API)
         └────► GPT (OpenAI API)
```

#### 实现示例

**配置文件** (`engine/llm_config.py`)：
```python
from dataclasses import dataclass
import os

@dataclass
class ModelConfig:
    provider: str  # "dashscope", "openai", "anthropic", "xai"
    model: str
    api_key_env: str
    temperature: float = 0.7
    max_tokens: int = 4000
    fallback_model: str = None

AGENT_MODEL_MAPPING = {
    "vision_agent": ModelConfig(
        provider="dashscope",
        model="qwen-vl-max",
        api_key_env="DASHSCOPE_API_KEY",
        temperature=0.5  # 视觉分析需要稳定性
    ),
    "selling_point_agent": ModelConfig(
        provider="xai",
        model="grok-beta",
        api_key_env="GROK_API_KEY",
        temperature=0.8,  # 营销文案需要创意
        fallback_model="qwen-plus"
    ),
    "script_agent": ModelConfig(
        provider="anthropic",
        model="claude-3-7-sonnet-20250219",
        api_key_env="ANTHROPIC_API_KEY",
        temperature=0.7,
        fallback_model="qwen-plus"
    ),
}

# 成本控制：高峰期自动降级
COST_AWARE_ROUTING = {
    "high_traffic_hours": [9, 10, 11, 14, 15, 16, 17],  # 工作时间
    "fallback_strategy": "always_use_qwen",  # 高峰期强制用便宜模型
}
```

**统一客户端** (`engine/llm_client.py`)：
```python
import litellm
from llm_config import AGENT_MODEL_MAPPING, COST_AWARE_ROUTING
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class UnifiedLLMClient:
    def __init__(self, agent_name: str):
        if agent_name not in AGENT_MODEL_MAPPING:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        self.agent_name = agent_name
        self.config = AGENT_MODEL_MAPPING[agent_name]
        
        # 设置 API Key
        api_key = os.getenv(self.config.api_key_env)
        if not api_key:
            logger.warning(f"{self.config.api_key_env} not set, will use fallback")
        
        # LiteLLM 全局配置
        litellm.set_verbose = False  # 生产环境关闭详细日志
        litellm.drop_params = True   # 自动过滤不支持的参数
    
    def chat(self, messages: list, **kwargs) -> str:
        """
        统一文本对话接口
        
        Args:
            messages: OpenAI格式的消息列表
            **kwargs: 额外参数（temperature, max_tokens等）
        
        Returns:
            模型回复的文本内容
        """
        model = self._select_model()
        
        try:
            response = litellm.completion(
                model=model,
                messages=messages,
                temperature=kwargs.get('temperature', self.config.temperature),
                max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
                api_key=os.getenv(self.config.api_key_env),
            )
            
            logger.info(
                f"LLM call success",
                extra={
                    "event": "llm.call.success",
                    "agent": self.agent_name,
                    "model": model,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                }
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.warning(
                f"LLM call failed: {e}",
                extra={
                    "event": "llm.call.failed",
                    "agent": self.agent_name,
                    "model": model,
                    "error": str(e)[:200]
                }
            )
            
            # 自动降级到备用模型
            if self.config.fallback_model:
                return self._call_fallback(messages, **kwargs)
            raise
    
    def multimodal(self, content: list, **kwargs) -> str:
        """
        多模态调用（支持图片/视频）
        
        Args:
            content: OpenAI格式的多模态内容列表
                     [{'type': 'text', 'text': '...'}, 
                      {'type': 'image_url', 'image_url': {...}}]
        """
        model = self._select_model()
        
        messages = [{'role': 'user', 'content': content}]
        
        try:
            response = litellm.completion(
                model=model,
                messages=messages,
                temperature=kwargs.get('temperature', self.config.temperature),
                api_key=os.getenv(self.config.api_key_env),
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Multimodal call failed: {e}")
            if self.config.fallback_model:
                return self._call_fallback(messages, **kwargs)
            raise
    
    def _select_model(self) -> str:
        """
        智能模型选择（支持成本控制）
        """
        # 成本控制：高峰期自动降级
        if COST_AWARE_ROUTING.get("fallback_strategy") == "always_use_qwen":
            current_hour = datetime.now().hour
            if current_hour in COST_AWARE_ROUTING["high_traffic_hours"]:
                logger.info(f"High traffic hour, using fallback model")
                return self.config.fallback_model or self.config.model
        
        return f"{self.config.provider}/{self.config.model}"
    
    def _call_fallback(self, messages: list, **kwargs) -> str:
        """
        备用模型调用
        """
        fallback_model = f"dashscope/{self.config.fallback_model}"
        logger.info(f"Calling fallback model: {fallback_model}")
        
        response = litellm.completion(
            model=fallback_model,
            messages=messages,
            temperature=kwargs.get('temperature', self.config.temperature),
            api_key=os.getenv("DASHSCOPE_API_KEY"),
        )
        return response.choices[0].message.content
```

**Agent中使用** (`engine/script_gen.py`)：
```python
from llm_client import UnifiedLLMClient

class ScriptGenerator:
    def __init__(self):
        # 使用统一客户端，自动选择配置的模型
        self.llm = UnifiedLLMClient(agent_name="script_agent")
    
    def generate_script(self, house_info: dict, timeline_data: list) -> str:
        # 构建Prompt（业务逻辑不变）
        prompt = self._build_prompt(house_info, timeline_data)
        
        messages = [
            {'role': 'system', 'content': 'You are a professional video script writer.'},
            {'role': 'user', 'content': prompt}
        ]
        
        # 统一调用接口，底层自动路由到配置的模型
        response = self.llm.chat(messages, temperature=0.7)
        
        return self._clean_response(response)
```

#### 环境变量配置

**新增环境变量** (`.env.example`)：
```bash
# ============ LLM 提供商 API Keys ============
# 阿里云通义千问（必填，作为fallback）
DASHSCOPE_API_KEY=sk-xxx

# X.AI Grok（可选，用于卖点提炼）
GROK_API_KEY=xai-xxx

# Anthropic Claude（可选，用于脚本生成）
ANTHROPIC_API_KEY=sk-ant-xxx

# OpenAI GPT（可选）
OPENAI_API_KEY=sk-xxx

# ============ LLM 策略配置 ============
# 成本控制：高峰期自动降级到便宜模型
LLM_COST_AWARE_ROUTING=true

# 重试策略
LLM_MAX_RETRIES=3
LLM_RETRY_DELAY=1  # 秒
```

#### LiteLLM 安装与配置

**安装** (`engine/requirements.txt`)：
```txt
litellm>=1.50.0
```

**模型提供商配置映射**：
```python
# LiteLLM 自动识别的模型前缀
"dashscope/qwen-vl-max"       → 阿里云 DashScope API
"grok-beta"                   → X.AI API (自动识别)
"claude-3-7-sonnet-20250219" → Anthropic API (自动识别)
"gpt-4o"                      → OpenAI API (自动识别)
"gemini/gemini-2.0-flash"    → Google Gemini API
```

#### 优势总结

1. **业务解耦**：Agent代码无需关心使用哪个模型，仅调用`llm.chat()`
2. **灵活切换**：修改配置文件即可全局切换模型，无需改代码
3. **成本优化**：高峰期自动降级、失败自动Fallback
4. **可观测性**：统一日志记录（模型、Token消耗、延迟）
5. **易于测试**：可轻松Mock `UnifiedLLMClient` 进行单元测试

### 2.3 技术栈升级策略

| 模块 | 当前技术 | 优化方案 | 升级理由 |
|------|---------|---------|---------|
| **多智能体框架** | 无（线性Celery任务链） | CrewAI / LangGraph | 支持Agent协作、状态回溯、迭代优化 |
| **视频理解** | Qwen-VL-Max（单帧/多帧） | Qwen-VL-Max + 视频直接理解 | 提升时序理解能力，识别动态亮点 |
| **脚本生成** | Qwen-Plus（单次调用） | Grok-4 / Claude 3.7 + Few-shot | 爆款脚本能力更强，可注入真实案例 |
| **视频剪辑** | MoviePy（静态对齐） | MoviePy + 智能节奏算法 | 动态速度控制、高光镜头自动前置 |
| **音频生成** | 阿里云CosyVoice | 保持 + 情绪化SSML增强 | 现有方案成熟，仅需强化情绪表达 |
| **视觉增强** | MoviePy TextClip | 保持 + 动态标注库 | 增加箭头指向、区域高亮等专业特效 |

## 三、各智能体详细设计

### 3.1 视频深度分析Agent

**角色定位**：专业实勘视频分析师，负责从原始素材中挖掘所有可用信息

#### 核心能力升级

##### 能力1：智能镜头切分与评分
**当前实现**：
- 使用PySceneDetect进行基于内容的镜头检测
- 通过Qwen-VL-Max分析单个片段的场景类型和特征

**优化方案**：
```
工作流程：
1. 镜头物理切分（PySceneDetect，阈值27.0）
2. 语义合并相邻镜头（通过Qwen-VL-Max多图推理）
3. 每个语义片段提取以下维度：
   - 场景类型（扩展至15个细分类别）
   - 视觉亮点（采光、景观、材质、空间感、功能亮点）
   - 情绪标签（惊艳/治愈/温馨/高级/遗憾）
   - 震撼度评分（1-10分，用于开头镜头筛选）
   - 适合节奏（快切/慢镜/定格）
```

**Prompt工程**（注入到Qwen-VL-Max）：
```
角色：你是10年经验的房产视频分析师，专门为短视频剪辑提供专业洞察。

任务：分析这段实勘视频，输出结构化分段数据。

评分标准（震撼度1-10分）：
- 10分：极致景观（270°江景、顶层露台）、超大空间（客厅>50㎡）
- 8-9分：高级材质（大理石、实木）、独特设计（岛台、衣帽间）
- 6-7分：良好采光、规整户型、新装修
- 4-5分：普通场景但功能完整
- 1-3分：模糊、杂乱、无亮点

情绪标签逻辑：
- 惊艳：意外的高配（超出总价预期的配置）
- 治愈：阳光、绿植、温馨色调
- 高级：极简设计、品质材料、留白
- 遗憾：明显缺陷（采光差、老旧、异味）

输出JSON格式：
{
  "segments": [
    {
      "start_sec": 0.0,
      "end_sec": 12.5,
      "scene": "客厅",
      "features": "270度落地窗，南向采光爆棚，实木地板",
      "highlight_tags": ["采光", "景观", "材质"],
      "emotion": "惊艳",
      "shock_score": 9,
      "suggested_pace": "慢镜",
      "potential_hook": true
    }
  ],
  "overall_quality": 8.5,
  "top_3_highlights": ["270°江景", "主卧超大衣帽间", "独立岛台厨房"]
}

关键约束：
- 片段必须按时间顺序且不重叠
- shock_score必须基于客观视觉元素，不主观夸大
- potential_hook=true的片段不超过2个
```

##### 能力2：动态亮点标注
**新增功能**：在视频分析阶段，自动标记需要文字标注的关键信息

```
标注触发逻辑：
- 空间数据（面积>30㎡的房间）
- 功能亮点（衣帽间、岛台、智能家居）
- 视野信息（江景、公园、学区）
- 稀缺配置（地暖、新风、智能马桶）

输出格式：
"annotations": [
  {
    "segment_index": 2,
    "timestamp": 15.3,
    "type": "area_label",
    "text": "主卧28㎡",
    "position": "bottom_right"
  },
  {
    "segment_index": 5,
    "timestamp": 32.8,
    "type": "feature_highlight",
    "text": "270°景观阳台",
    "position": "center",
    "style": "arrow_point"
  }
]
```

### 3.2 卖点提炼Agent

**角色定位**：资深房产营销专家，负责从分析数据中提炼核心卖点并确定视频调性

#### 工作流程

```
输入数据：
- 视频分析结果（segments + top_3_highlights）
- 房源基础数据（总价、面积、户型、小区、楼层）

处理逻辑：
1. 综合评估：总价 vs 配置 → 性价比判断
2. 竞争定位：同板块同价位对比 → 差异化卖点
3. 调性选择：
   - 惊艳系：低总价+高配置（如300万买到江景三房）
   - 性价比系：刚需盘+实用功能齐全
   - 治愈系：采光+景观+温馨装修
   - 反转系：外观普通但内部惊艳
   - 真实系：优缺点并存，强调真实体验

输出结构：
{
  "core_selling_points": [
    "358万拿下滨江三房",
    "270度落地窗看江景",
    "主卧带独立衣帽间"
  ],
  "video_style": "惊艳系",
  "hook_strategy": "价格反差",
  "honest_flaws": ["楼层偏高，等电梯时间较长"],
  "target_audience": "首次置业刚需家庭"
}
```

#### Prompt工程（注入到Grok-4 / Claude 3.7）

```
角色：你是拥有500万粉丝的探房博主，擅长从普通房子中挖掘爆款内容。

背景数据：
- 房源：总价{price}万，{area}㎡，{layout}，{community}，{floor}楼
- 视频分析：{analysis_result}

任务流程：
1. 卖点提炼（3-6个，按吸引力排序）
   - 优先选择"反差感"（价格低但配置高、外观旧但内饰新）
   - 必须包含1个客观数据（面积、总价、景观）
   - 必须包含1个情感价值（治愈、温馨、高级感）

2. 调性判断（只能选1个）
   - 惊艳系：适用于shock_score≥8的片段占比>40%
   - 性价比系：总价<板块均价且功能完整
   - 治愈系：采光+绿植+温馨色调
   - 反转系：开头平淡但后续高光
   - 真实系：优缺点明显但整体性价比高

3. 钩子设计（前3秒必杀技）
   公式：{total_price}万+{location}+{unexpected_feature}
   示例："358万！滨江三房！居然还带270°江景阳台？"

4. 真实槽点（增强可信度）
   - 必须基于视频中的客观观察
   - 控制在1-2个，不能影响整体评价
   - 示例："唯一遗憾是楼层高了点，赶时间的朋友可能要等电梯"

输出JSON：
{
  "core_selling_points": ["卖点1", "卖点2", "卖点3"],
  "video_style": "惊艳系",
  "hook_sentence": "358万！滨江三房！270°江景阳台谁能拒绝？",
  "honest_flaws": ["楼层偏高"],
  "rhythm_advice": "开头快切3个高光→中段慢镜细节→结尾快速收束"
}
```

### 3.3 脚本创作Agent

**角色定位**：专业视频文案创作者，负责生成爆款解说词

#### 核心升级点

##### 1. 爆款脚本六要素
```
结构设计（45-60秒总时长）：
├─ 开场钩子（3秒）：价格+位置+反差
├─ 快速概览（8-12秒）：户型+核心卖点速览
├─ 亮点递进（25-35秒）：3-4个场景细节描述
│   └─ 情绪化表达：不说"采光好"，说"阳光洒满客厅，治愈感拉满"
├─ 真实槽点（3-5秒）：增强可信度
└─ 互动结尾（5-8秒）：问值不值+引导评论

语气规范：
- 必须用"哎""真的""居然"等口语化词汇
- 避免书面语："该房源拥有"→"这套房子有"
- 情绪化："不错"→"爱了"、"可以"→"绝了"
```

##### 2. 时长精算机制（升级现有实现）
**当前问题**：
- 固定3.5字/秒预算，未考虑情绪停顿和语气词
- 音频生成后通过变速对齐，影响自然度

**优化方案**：
```
动态语速模型：
- 开场钩子：4字/秒（快速抓取注意力）
- 亮点描述：3字/秒（舒缓、有情感）
- 转折槽点：3.5字/秒（正常语速）
- 互动结尾：3字/秒（留白引导思考）

预算分配算法：
for segment in timeline:
    segment_type = classify_segment_type(segment)  # 钩子/亮点/槽点/结尾
    char_per_sec = get_dynamic_rate(segment_type)
    char_budget = floor(segment.duration * char_per_sec * 0.95)  # 留5%安全边际
```

##### 3. Prompt工程（整合现有实现）

**对比现有Prompt**：
```diff
- "你是一位专业的房产短视频解说达人"
+ "你是10年经验、粉丝500万的探房博主，百万播放视频超200条"

- "情绪化表达"（过于抽象）
+ "具体例子：不说'采光好'，说'阳光洒满每个角落，治愈感拉满'"

+ 新增：Few-shot Learning（注入2-3个真实爆款脚本示例）
+ 新增：反面案例（避免模板化、避免夸张堆砌）
```

**完整Prompt模板**：
```
# Role
你是10年经验探房博主，粉丝500万，擅长"温情生活风"视频创作。
代表作品：《358万滨江三房，270°江景谁能拒绝》（播放量180万）

# Context Data
房源信息：{house_info}
卖点分析：{selling_points}
视频调性：{video_style}
片段时长预算：{timeline_with_budget}

# Task
生成45-60秒探房视频解说词，必须包含：
1. 开场钩子（3秒）
2. 分段解说词（对应每个视频片段）
3. 互动结尾（5-8秒）

# 爆款脚本六要素
1. 开场钩子：{hook_sentence}（已提供，可微调）
2. 快速概览：户型+核心卖点速览（8-12秒）
3. 亮点递进：3-4个场景细节，情绪化表达
   - ✅ "阳光洒满客厅，治愈感拉满"
   - ❌ "客厅采光良好"
4. 真实槽点：{honest_flaws}（必须提及，增强可信度）
5. 互动结尾：问值不值+引导评论

# 时长约束（严格遵守）
每个片段的char_budget已计算（3-4字/秒），超出会导致音视频不同步。
宁可少写3-5字，不要超预算。

# Few-shot Examples
【示例1：惊艳系】
片段1（客厅，5秒，预算17字）："哎，这个客厅！270度落地窗，江景尽收眼底。"
片段2（主卧，6秒，预算20字）："主卧更绝，28㎡还带独立衣帽间，这配置爱了。"

【示例2：性价比系】
片段1（厨房，5秒，预算17字）："厨房虽小但功能齐全，岛台设计太实用了。"
片段2（阳台，4秒，预算14字）："阳台看出去是公园，遛娃方便。"

# 输出格式（严格JSON）
{
  "intro_text": "大家好，今天带大家看...",
  "intro_card": {
    "headline": "滨江·中南春溪集",
    "specs": "89㎡ | 三室两厅",
    "highlights": ["江景房", "精装修", "急售"]
  },
  "segments": [
    {
      "asset_id": "uuid-1",
      "text": "解说词...",
      "visual_prompt": "English prompt for AI filter (if needed)",
      "audio_cue": "SFX suggestion (door open / footsteps / wow)"
    }
  ]
}
```

### 3.4 智能剪辑Agent

**角色定位**：专业剪辑师，负责将素材按最佳节奏剪辑成片

#### 核心升级策略

##### 1. 高光镜头自动前置
**设计逻辑**：
```
前3秒素材选择算法：
1. 筛选 shock_score ≥ 8 的所有片段
2. 优先级排序：
   - P0：江景/大景观（emotion="惊艳"）
   - P1：超大空间（客厅>40㎡，主卧>25㎡）
   - P2：独特设计（岛台、衣帽间、露台）
3. 从选中片段中截取最具冲击力的1-3秒
4. 如果该片段原本在中后段，标记"已前置"，避免重复使用
```

**实现方式**：
```
伪代码：
def select_opening_shot(segments, script_hook_duration=3):
    # 1. 筛选候选
    candidates = [s for s in segments if s['shock_score'] >= 8]
    
    # 2. 排序
    candidates.sort(key=lambda s: (
        1 if s['emotion'] == '惊艳' else 0,
        s['shock_score'],
        s['start_sec']  # 越早出现优先级越低（制造悬念）
    ), reverse=True)
    
    # 3. 提取片段
    best_shot = candidates[0]
    clip_start = best_shot['start_sec']
    clip_duration = min(script_hook_duration, best_shot['end_sec'] - clip_start)
    
    # 4. 标记已使用
    best_shot['used_in_hook'] = True
    
    return {
        'source_segment_id': best_shot['asset_id'],
        'extract_start': clip_start,
        'extract_duration': clip_duration
    }
```

##### 2. 动态节奏控制
**当前实现**：
- 视频时长强制对齐音频（慢镜头0.85x或定帧填充）

**优化方案**：
```
智能速度调节矩阵：

片段类型       建议速度      应用场景
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
开场钩子       1.15x         快速抓取注意力
快速概览       1.0-1.1x      流畅过渡
亮点细节       0.85-0.95x    突出质感、材质
情绪高潮       0.75x         慢镜头强化冲击
真实槽点       1.0x          正常速度保持客观
互动结尾       0.9x          留白引导思考

算法逻辑：
if segment.emotion == "惊艳" and segment.shock_score >= 9:
    target_speed = 0.75  # 超级慢镜
elif segment.scene_type in ["开场", "概览"]:
    target_speed = 1.1
elif segment.text contains ["缺点", "遗憾", "不足"]:
    target_speed = 1.0  # 不美化缺点
else:
    target_speed = 0.9  # 默认舒缓节奏
```

##### 3. 转场智能选择
**设计原则**：
```
转场类型映射：

场景切换                  转场效果
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
同房间不同角度             无转场 / 溶解
不同房间相邻               滑动 / 缩放
空间跨度大（室内→室外）     模糊 / 淡入淡出
情绪转折（亮点→槽点）       硬切（强调对比）
高潮镜头前                 放大缩放（制造期待）

实现方式：
- MoviePy的 crossfadein / crossfadeout
- 自定义transition函数（基于OpenCV）
```

### 3.5 音频编排Agent

**角色定位**：音频总监，负责配音、BGM、音效的完美混音

#### 核心能力升级

##### 1. 情绪化TTS增强
**当前实现**：
- CosyVoice生成自然语音
- 通过speech_rate控制语速（0.85-1.25x）
- 已支持基础SSML标注（项目中已使用`_text_to_emotional_ssml`函数）

**优化方案**（基于阿里云CosyVoice官方SSML能力）：
```
支持的SSML标签（v3-flash/v3-plus/v2模型）：

标签           参数                   适用场景               示例
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<speak>       rate="0.5-2.0"        全局语速控制           <speak rate="1.2">...</speak>
<break>       time="毫秒/秒"        插入停顿               走<break time="500ms"/>进去看看
<phoneme>     ph="拼音"             多音字消歧             银<phoneme ph="hang2">行</phoneme>
<say-as>      interpret-as="..."   数字/日期朗读方式      <say-as interpret-as="digits">123</say-as>
<sub>         alias="替换词"        文本替换               <sub alias="人工智能">AI</sub>
<p> / <s>     -                     段落/句子边界          <p>第一段</p><p>第二段</p>

重要约束：
1. 仅复刻音色和标记为支持SSML的系统音色可用（如longanyang）
2. 仅非流式和单向流式调用支持SSML
3. XML特殊字符必须转义（& → &amp;, < → &lt;, > → &gt;, " → &quot;）
4. 不支持<emotion>标签（官方文档未列出）

实战优化策略：

场景类型         SSML组合                                  效果
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
开场钩子         <speak rate="1.3">...</speak>             快速抓取注意力
亮点强调         文字<break time="300ms"/>真的绝了        停顿制造悬念
数字展示         <say-as interpret-as="cardinal">358万    清晰朗读价格
多音字校正       银<phoneme ph="hang2">行</phoneme>       避免误读
品牌名称         <sub alias="中南春溪集">项目名</sub>      规范化朗读
互动结尾         值不值<break time="500ms"/>             引导思考

实现方式（扩展现有audio_gen.py）：
def _text_to_emotional_ssml_v2(text: str, segment_metadata: dict) -> str:
    """
    基于CosyVoice官方SSML能力增强表达力
    """
    # 1. 转义XML特殊字符
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    # 2. 多音字校正（基于预定义词典）
    phoneme_dict = {
        '银行': '银<phoneme ph="hang2">行</phoneme>',
        '重庆': '<phoneme ph="chong2">重</phoneme>庆'
    }
    for word, ssml in phoneme_dict.items():
        text = text.replace(word, ssml)
    
    # 3. 数字智能处理
    import re
    text = re.sub(r'(\d+)万', r'<say-as interpret-as="cardinal">\1</say-as>万', text)
    text = re.sub(r'(\d+)㎡', r'<say-as interpret-as="cardinal">\1</say-as>平米', text)
    
    # 4. 情绪停顿（基于关键词）
    emotion_keywords = ['真的', '居然', '竟然', '绝了', '爱了']
    for keyword in emotion_keywords:
        if keyword in text:
            text = text.replace(keyword, f'<break time="200ms"/>{keyword}')
    
    # 5. 全局语速控制
    if segment_metadata.get('is_hook'):
        rate = 1.3  # 开场快速
    elif segment_metadata.get('emotion') == '惊艳':
        rate = 0.9  # 亮点舒缓
    else:
        rate = 1.0
    
    return f'<speak rate="{rate}">{text}</speak>'
```

##### 2. BGM智能匹配与动态混音
**当前实现**：
- 从预设列表随机选择BGM
- 固定音量15%，循环播放

**优化方案**：
```
BGM选择决策树：

视频调性      BGM风格           代表曲目关键词
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
惊艳系        轻奢电子/钢琴      elegant piano, modern electronic
性价比系      轻快吉他          acoustic guitar, upbeat
治愈系        温暖原声          warm acoustic, healing
反转系        悬念→明快          suspense intro + bright chorus
真实系        朴实民谣          folk, natural

动态音量曲线（Auto-ducking升级）：

时间轴         BGM音量      TTS音量
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
开场钩子       5%           100%（突出语音）
快速概览       15%          100%
亮点细节       20%          95%（音乐渲染情绪）
高潮慢镜       30%          90%（音乐配合画面）
真实槽点       10%          100%（保持清晰）
互动结尾       25%          95%

实现算法（基于现有auto_ducking）：
def intelligent_bgm_mixing(tts_segments, bgm_clip, video_style):
    volume_curve = []
    for seg in tts_segments:
        if seg['is_hook']:
            bgm_vol = 0.05
        elif seg['emotion'] == '惊艳' and seg['shock_score'] >= 9:
            bgm_vol = 0.30  # 音乐配合高潮
        elif '缺点' in seg['text'] or '遗憾' in seg['text']:
            bgm_vol = 0.10  # 降低音乐避免掩盖客观评价
        else:
            bgm_vol = 0.15  # 默认
        
        volume_curve.append({
            'start': seg['start'],
            'duration': seg['duration'],
            'volume': bgm_vol
        })
    
    return apply_dynamic_volume(bgm_clip, volume_curve)
```

##### 3. 音效智能插入（SFX升级）
**当前实现**：
- 基于script的audio_cue字段手动匹配

**优化方案**：
```
自动音效触发规则：

场景事件              触发音效           插入时机
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
进门镜头              door_open.mp3      片段开始0.5s
脚步移动（走廊）      footsteps.wav      全片段循环
惊讶语气（"哇""绝了"）wow_gasp.mp3      关键词出现时刻
数字展示（面积/总价） number_pop.mp3     字幕弹出时
景观镜头              birds_ambient.wav  背景环境音

实现方式（扩展现有sfx_library.py）：
class IntelligentSFXMatcher:
    def auto_select_sfx(self, segment: dict) -> list:
        sfx_list = []
        
        # 规则1：场景类型匹配
        if segment['scene'] == '走廊':
            sfx_list.append({
                'file': 'footsteps.wav',
                'start_offset': 0,
                'volume': 0.2,
                'loop': True
            })
        
        # 规则2：情绪关键词匹配
        text = segment['text']
        if any(word in text for word in ['哇', '绝了', '爱了']):
            keyword_pos = self._find_keyword_position(text)
            sfx_list.append({
                'file': 'wow_gasp.mp3',
                'start_offset': keyword_pos * 3.5,  # 假设3.5字/秒
                'volume': 0.4,
                'loop': False
            })
        
        # 规则3：视觉标注同步
        if segment.get('annotations'):
            for anno in segment['annotations']:
                if anno['type'] == 'area_label':
                    sfx_list.append({
                        'file': 'number_pop.mp3',
                        'start_offset': anno['timestamp'],
                        'volume': 0.3,
                        'loop': False
                    })
        
        return sfx_list
```

### 3.6 视觉增强Agent

**角色定位**：视觉设计师，负责字幕、标注、特效的专业化呈现

#### 核心能力升级

##### 1. 动态字幕样式系统
**当前实现**：
- 固定样式字幕（黄色、居中、逐句显示）

**优化方案**：
```
字幕样式映射表：

内容类型           字体大小    颜色        特效
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
开场钩子           120px      亮黄        打字机效果
核心卖点关键词     100px      金色        缩放弹出
亮点描述          80px       白色        淡入淡出
数字/价格         110px      红色        跳动强调
真实槽点          75px       灰白        平滑出现
互动问句          90px       白色        闪烁提示

实现方式（扩展现有_generate_subtitle_clips）：
def create_dynamic_subtitle(text, segment_metadata, video_size):
    # 1. 识别内容类型
    if segment_metadata.get('is_hook'):
        style = HOOK_STYLE  # 大字+打字机
        animation = 'typewriter'
    elif re.search(r'\d+万|\d+㎡', text):
        style = NUMBER_STYLE  # 数字强调
        animation = 'bounce'
    elif segment_metadata.get('emotion') == '惊艳':
        style = HIGHLIGHT_STYLE  # 金色+缩放
        animation = 'scale_in'
    else:
        style = DEFAULT_STYLE
        animation = 'fade'
    
    # 2. 应用动画
    subtitle_clip = create_animated_text(
        text,
        style=style,
        animation=animation,
        duration=segment_metadata['duration']
    )
    
    return subtitle_clip
```

##### 2. 智能区域标注
**设计方案**：
```
标注类型设计：

类型              样式                  触发条件
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
面积标签          矩形框+数字           面积>25㎡的房间
景观指向          箭头+文字             提到"江景""公园"
功能圈选          圆形高亮             岛台、衣帽间特写
材质说明          半透明标签           大理石、实木特写
距离信息          虚线+图标            "距地铁500米"

实现伪代码：
def generate_annotation_clip(annotation_data, video_size, segment_duration):
    if annotation_data['type'] == 'arrow_point':
        # 创建箭头SVG → 转为ImageClip → 定位到指定区域
        arrow_clip = create_arrow_graphic(
            start_pos=annotation_data['arrow_start'],
            end_pos=annotation_data['arrow_end'],
            color='#FFD700'
        )
        
        text_clip = TextClip(
            annotation_data['text'],
            fontsize=60,
            color='white',
            bg_color='rgba(0,0,0,0.7)'
        ).set_position(annotation_data['text_position'])
        
        return CompositeVideoClip([arrow_clip, text_clip])
        .set_duration(segment_duration)
        .crossfadein(0.3)
```

### 3.7 总导演Agent（Orchestrator）

**角色定位**：全局协调者，负责智能体间的协作、质量把控和迭代优化

#### 核心职责

##### 1. 工作流编排
```
主流程设计：

阶段                子任务                     输出
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
① 视频理解阶段    视频深度分析Agent          segments + highlights
                 ↓
② 内容策划阶段    卖点提炼Agent              selling_points + style
                 ↓
                 脚本创作Agent              script + intro_card
                 ↓
③ 质量检查点      【检查1】时长预算是否超标？
                 【检查2】是否包含真实槽点？
                 【检查3】开场钩子是否足够吸引？
                 ↓
                 ✓ 通过 → 进入剪辑阶段
                 ✗ 失败 → 回退到脚本创作Agent重新生成
                 ↓
④ 视频制作阶段    智能剪辑Agent              video_timeline
                 音频编排Agent              audio_tracks
                 视觉增强Agent              subtitle + annotations
                 ↓
⑤ 最终合成        视频渲染引擎               final_video.mp4
```

##### 2. 质量把控规则
```
质量检查清单（Quality Gates）：

检查点                        标准                    不通过处理
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
开场钩子强度               包含价格+位置+反差        回退重新生成hook_sentence
时长预算准确性             每片段文案≤预算+5%       裁剪超长文案或调整片段时长
真实性检查                 必须包含1-2个槽点         补充honest_flaws
情绪化表达                 避免"不错""可以"等弱词   替换为"爱了""绝了"
视频节奏合理性             快-慢-快结构清晰         调整片段速度分配
音频混音平衡               BGM不掩盖TTS             动态调整auto_ducking参数

实现方式（伪代码）：
class OrchestratorAgent:
    def validate_script(self, script, timeline):
        errors = []
        
        # 检查1：时长预算
        for seg in script['segments']:
            char_count = len(seg['text'])
            time_budget = timeline[seg['asset_id']]['duration']
            max_chars = time_budget * 3.5 * 1.05  # 允许5%超出
            if char_count > max_chars:
                errors.append({
                    'type': 'budget_overflow',
                    'segment_id': seg['asset_id'],
                    'exceed_by': char_count - max_chars
                })
        
        # 检查2：真实性
        honest_flaws = script.get('honest_flaws', [])
        if not honest_flaws or len(honest_flaws) == 0:
            errors.append({
                'type': 'missing_flaws',
                'suggestion': '缺少真实槽点，可能降低可信度'
            })
        
        # 检查3：钩子强度
        hook = script.get('hook_sentence', '')
        if not any(pattern in hook for pattern in ['万', '㎡', '居然', '？']):
            errors.append({
                'type': 'weak_hook',
                'current_hook': hook,
                'suggestion': '钩子缺少价格/反差/疑问'
            })
        
        return errors
    
    def handle_validation_failure(self, errors, context):
        if any(e['type'] == 'budget_overflow' for e in errors):
            # 策略1：要求脚本Agent重新生成
            return self.call_script_agent_with_feedback(
                context,
                feedback="部分片段文案超出时长预算，请精简表达"
            )
        
        if any(e['type'] == 'weak_hook' for e in errors):
            # 策略2：仅重新生成开场部分
            return self.call_selling_point_agent(
                context,
                focus='hook_only'
            )
```

##### 3. 迭代优化机制
```
自适应学习流程：

用户反馈              优化动作                   持久化存储
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
视频时长不满意        调整全局speech_rate基线    config: target_video_length
某个片段音视频不同步  重新计算该场景的字数预算   DB: scene_char_budget_override
字幕样式不喜欢        切换subtitle_style配置     config: preferred_subtitle_style
BGM与调性不匹配       更新video_style→BGM映射    config: style_bgm_mapping

实现方式：
- 在project表增加user_preferences字段（JSONB）
- 在render_video任务中读取并应用偏好
- 通过API允许用户在review阶段提交偏好调整
```

## 四、实现路径规划

### 4.1 技术集成方案

#### 方案A：渐进式升级（推荐用于MVP）
```
阶段划分：

Phase 1（立即可做）：Prompt工程优化
- 升级vision.py中的分析Prompt，增加震撼度评分
- 升级script_gen.py的Prompt，注入爆款脚本示例
- 升级audio_gen.py，增加情绪化SSML标注
工作量：2-3天
效果：脚本质量提升30%+，音频更自然

Phase 2（1周内）：智能剪辑算法
- 实现高光镜头自动前置（_select_opening_shot）
- 实现动态速度控制矩阵（_apply_intelligent_speed）
- 升级转场选择逻辑（_smart_transition）
工作量：5-7天
效果：视频节奏明显优化，开场吸引力提升

Phase 3（2周内）：视觉增强系统
- 实现动态字幕样式（根据内容类型自动切换）
- 实现智能区域标注（箭头、高亮、标签）
- 集成音效自动匹配器（IntelligentSFXMatcher）
工作量：10-14天
效果：视频专业度大幅提升

Phase 4（1个月）：多智能体框架集成
- 引入LangGraph或CrewAI
- 实现OrchestratorAgent质量检查
- 支持迭代优化和用户偏好学习
工作量：20-30天
效果：系统可自我优化，适应不同用户风格
```

#### 方案B：全面重构（适用于长期战略）
```
架构调整：
1. 新增ai-agents服务（Python + LangChain）
   - 独立部署，专门负责智能体协作
   - 通过消息队列与现有engine通信

2. 升级engine为纯执行层
   - 仅保留视频渲染、音频合成等IO密集任务
   - 所有AI决策由ai-agents服务完成

3. 引入实验平台
   - A/B测试不同Prompt版本
   - 收集用户反馈训练奖励模型
   - 自动化迭代Prompt优化

技术栈：
- 智能体框架：LangGraph（支持状态回溯和复杂协作）
- 编排引擎：Temporal / Prefect（更可靠的工作流管理）
- 模型路由：LiteLLM（统一调用Grok/Claude/Qwen）
- 效果监控：Weights & Biases（追踪每个视频的质量指标）

工作量：2-3个月
收益：完全工业化的AI视频生成系统
```

### 4.2 关键风险与应对

| 风险项 | 影响 | 应对策略 |
|-------|------|---------|
| **大模型API成本** | 视频分析+脚本生成成本增加50%+ | ① 缓存相似房源的分析结果<br>② 优先使用Qwen（性价比高）<br>③ 高峰期降级为简化Prompt |
| **生成质量不稳定** | 部分视频脚本仍显模板化 | ① Few-shot Learning强制对齐风格<br>② 质量检查不通过自动重试<br>③ 人工审核兜底机制 |
| **渲染性能下降** | 复杂特效导致渲染时间×2 | ① 特效分级（简单/标准/专业）<br>② 预渲染缓存常用元素<br>③ 多线程并行处理 |
| **多智能体复杂度** | 开发和调试难度增加 | ① Phase 1仅用Prompt优化，不引入框架<br>② 逐步迁移，保持后向兼容<br>③ 完善日志和可观测性 |

### 4.3 效果评估指标

```
量化指标体系：

维度              指标                     目标值         当前基线
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
用户满意度        视频一次通过率            ≥85%          ~60%
                重新生成次数              ≤1.5次/视频    ~2.5次
内容质量          脚本情绪化词汇占比        ≥20%          ~8%
                开场钩子强度评分          ≥8/10         ~6/10
                真实槽点覆盖率            100%          ~40%
技术性能          音视频同步误差            ≤0.3秒        ~0.8秒
                视频生成总时长            ≤5分钟        ~8分钟
                渲染失败率                ≤2%           ~5%
业务价值          视频播放完成率            ≥70%          未统计
                用户评论互动率            ≥5%           未统计

数据采集方案：
- 在project表增加quality_metrics字段（JSONB）
- 在前端review页面增加"满意度评分"入口
- 通过Webhook对接抖音/小红书数据（如已发布）
```

## 五、总结与建议

### 核心优化亮点

1. **从流水线到智能体**：通过引入总导演Agent和质量检查机制，实现真正的"智能"而非"自动化"
2. **爆款逻辑工程化**：将专业博主的经验（钩子设计、节奏控制、真实槽点）转化为可执行的Prompt和算法
3. **渐进式升级路径**：Phase 1仅需3天即可见效，避免大规模重构风险

### 立即可行动项（优先级P0）

```
第一周工作清单：
□ 升级vision.py：增加震撼度评分（shock_score）和情绪标签
□ 升级script_gen.py：注入2-3个真实爆款脚本作为Few-shot示例
□ 升级audio_gen.py：实现基于官方SSML的智能标注（多音字、数字、停顿）
□ 实现高光镜头前置逻辑（修改video_render.py的render_video方法）
□ 增加开场钩子强度检查（在TaskQueueService或tasks.py中）
□ 配置Grok-4 API（如预算允许），用于脚本生成

预期效果：
- 视频开场吸引力提升40%+
- 脚本真实感和情绪化表达明显改善
- TTS语音自然度提升（停顿、数字朗读更清晰）
- 用户重新生成次数下降30%
```

### 长期战略建议

1. **建立视频质量评估体系**：通过用户反馈和播放数据，训练视频质量预测模型
2. **打造行业垂直大模型**：基于积累的房产视频数据，微调专属的"探房文案大模型"
3. **拓展多场景支持**：在房产之外，探索民宿、商铺、办公空间等垂直领域

---

**设计文档版本**：v1.0  
**最后更新**：2026-01-13  
**下一步行动**：等待用户确认优先级，启动Phase 1开发
