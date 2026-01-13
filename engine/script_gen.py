import json
from http import HTTPStatus
from dashscope import Generation
from config import Config
import math

class ScriptGenerator:
    def __init__(self):
        if not Config.DASHSCOPE_API_KEY:
            raise ValueError("DASHSCOPE_API_KEY is not set")

    def generate_script(self, house_info: dict, timeline_data: list) -> str:
        """
        Generate a video script based on house info and ordered asset timeline.
        Returns a JSON string of object structure:
        {
            "intro_text": "开场白...",
            "segments": [{"asset_id": "...", "text": "..."}]
        }
        """
        
        # 1. Build Context with Time Budget
        # Use 3.5 chars/second (slightly conservative) to ensure audio fits video duration
        # This accounts for natural pauses and breathing in TTS
        CHARS_PER_SECOND = 3.5
        
        context_str = f"房源信息：{json.dumps(house_info, ensure_ascii=False)}\n\n"
        context_str += "视频片段顺序及时长预算：\n"
        
        for idx, item in enumerate(timeline_data):
            scene = item.get('scene_label', '未知场景')
            duration = float(item.get('duration', 5.0))
            # Budget: ~3.5 chars per second (conservative to avoid audio > video)
            word_budget = math.floor(duration * CHARS_PER_SECOND)
            asset_id = item.get('id') or item.get('asset_id') or 'unknown'
            
            context_str += f"片段{idx+1} [ID: {asset_id}]: {scene} (时长: {duration:.1f}秒, 严格字数限制: {word_budget}字)\n"

        # 2. Prompt Engineering with Few-shot Learning
        prompt = f"""
# Role
你是10年经验、粉丝500万的探房博主，百万播放视频超200条。
代表作品：《358万滨江三房，270°江景谁能拒绝》（播放量180万）
擅长风格：“温情生活风”视频创作，强调真实感和情感共鸣。

# Context Data
{context_str}

# Task
生成45-60秒探房视频解说词，必须包含：
1. 开场白（intro_text）：大家好+房源简介+引导语
2. 片头卡片（intro_card）：位置、户型、卖点
3. 分段解说词（segments）：对应每个视频片段

# 爆款脚本六要素

## 1. 开场钩子（3秒）
**公式**：总价 + 位置 + 反差/疑问
**示例**：
- "❌ 反例："这套房子不错" → 太平淡
- "✅ 正例："358万！滨江三房！居然还带270°江景阳台？" → 价格+位置+意外

## 2. 快速概览（8-12秒）
**要点**：户型+核心卖点速览，避免堆砸
**示例**：
- "❌ 反例："这是一套三室两厅两卫的房子，面积98平米" → 书面语
- "✅ 正例："三房两厅，98平，南北通透，生活阳台超大" → 简洁有力

## 3. 亮点递进（25-35秒）
**情绪化表达原则**：
- ❌ 不说"采光好" → ✅ "阳光洒满客厅，治愈感拉满"
- ❌ 不说"空间大" → ✅ "这个客厅，真的大到让人安心"
- ❌ 不说"装修不错" → ✅ "这个质感，一看就是用心装的"

**语气词库**（必须使用）：哎、真的、居然、绝了、爱了、谁能拒绝

## 4. 真实槽点（3-5秒）
**必须提及1-2个缺点，增强可信度**：
- "唯一遗憾是楼层高了点，赶时间的朋友可能要等电梯"
- "小区年代比较久，但胜在地段好、配套成熟"
- "厨房空间不算大，但岛台设计弥补了收纳"

## 5. 互动结尾（5-8秒）
**公式**：问值不值 + 引导评论
**示例**：
- "总价358万，滨江三房，你觉得值不值？评论区聊聊你的看法"
- "这样的房子，你会考虑吗？喜欢的话点个关注"

# Few-shot Examples（真实爆款案例）

## 示例1：惊艳系（270°江景房）
```json
{{
  "intro_text": "大家好，今天带大家看的是位于滨江的一套三房，总价358万，最特别的是它有270度的江景阳台，走，进去感受一下！",
  "intro_card": {{
    "headline": "滨江·中南春溪集",
    "specs": "89㎡ | 三室两厅",
    "highlights": ["江景房", "精装修", "急售"]
  }},
  "segments": [
    {{
      "asset_id": "segment-1",
      "text": "哎，这个客厅！270度落地窗，江景尽收眼底。",
      "visual_prompt": "Panoramic river view living room, floor-to-ceiling windows, golden hour lighting",
      "audio_cue": "Subtle wow effect"
    }},
    {{
      "asset_id": "segment-2",
      "text": "主卧更绝，28㎡还带独立衣帽间，这配置爱了。",
      "visual_prompt": "Spacious master bedroom with walk-in closet, warm lighting",
      "audio_cue": "Footsteps"
    }},
    {{
      "asset_id": "segment-3",
      "text": "唯一遗憾是楼层高了点，但胜在视野好啊。",
      "visual_prompt": "High floor view, cityscape",
      "audio_cue": null
    }},
    {{
      "asset_id": "segment-4",
      "text": "总价358万，滨江三房，你觉得值不值？",
      "visual_prompt": "Overview shot of the property",
      "audio_cue": "Light BGM fade out"
    }}
  ]
}}
```

## 示例2：性价比系（小三房实用温馨）
```json
{{
  "intro_text": "大家好，今天看的这套小三房虽然面积不大，但胜在布局合理、功能完善，走，进去看看！",
  "intro_card": {{
    "headline": "城西·绿城翡翠城",
    "specs": "78㎡ | 三室两厅",
    "highlights": ["南北通透", "近地铁", "学区房"]
  }},
  "segments": [
    {{
      "asset_id": "segment-1",
      "text": "客厅虽然不大，但阳光洒满每个角落，治愈感拉满。",
      "visual_prompt": "Cozy living room with abundant natural light, warm atmosphere",
      "audio_cue": "Morning birds chirping"
    }},
    {{
      "asset_id": "segment-2",
      "text": "厨房空间不算大，但岛台设计太实用了。",
      "visual_prompt": "Compact kitchen with island counter, efficient design",
      "audio_cue": "Subtle kitchen sounds"
    }},
    {{
      "asset_id": "segment-3",
      "text": "阳台看出去是公园，運娃方便，这就是生活啊。",
      "visual_prompt": "Balcony view overlooking park, greenery",
      "audio_cue": "Park ambience"
    }},
    {{
      "asset_id": "segment-4",
      "text": "这样的小三房，你会考虑吗？评论区聊聊。",
      "visual_prompt": "Final overview",
      "audio_cue": null
    }}
  ]
}}
```

# 时长约束（极其重要）

**动态语速模型**：
- 开场钩子：4字/秒（快速抓取注意力）
- 亮点描述：3字/秒（舒缓、有情感）
- 转折槽点：3.5字/秒（正常语速）
- 互动结尾：3字/秒（留白引导思考）

**关键规则**：
1. 必须严格遵守每个片段的"字数限制"
2. 宁可少写3-5字，不要超出预算（超出导致音视频不同步）
3. 留出5%安全边际

# 结构化输出要求

必须返回一个 JSON 对象，格式如下：
```json
{{
  "intro_text": "开场白语音文案...",
  "intro_card": {{
    "headline": "位置·小区名",
    "specs": "面积 | 户型",
    "highlights": ["卖点1", "卖点2", "卖点3"]
  }},
  "segments": [
    {{
      "asset_id": "片段ID",
      "text": "解说词内容...",
      "visual_prompt": "English prompt for AI video filter",
      "audio_cue": "SFX suggestion"
    }}
  ]
}}
```

**不要**改变 asset_id，必须原样返回。

# 反面案例（避免以下错误）

❌ 模板化："这套房子不错" / "可以考虑" → 太平淡
❌ 书面语："该房源拥有" / "配备齐全" → 不自然
❌ 夹大堆砸："客厅很大采光好装修高级" → 信息过载
❌ 无槽点：只说好话 → 缺乏真实感

# Action
请直接输出 JSON，不要包含 Markdown 代码块标记或其他废话。
"""

        messages = [
            {'role': 'system', 'content': 'You are a professional video script writer. You output strict JSON.'},
            {'role': 'user', 'content': prompt}
        ]

        # 3. Call Qwen-Plus
        response = Generation.call(model='qwen-plus',
                                   messages=messages,
                                   result_format='message',
                                   temperature=0.7)

        if response.status_code == HTTPStatus.OK:
            content = response.output.choices[0].message.content
            # Post-processing to clean up common artifacts
            clean_script = content.strip()
            if clean_script.startswith("```json"):
                clean_script = clean_script[7:]
            elif clean_script.startswith("```"):
                clean_script = clean_script[3:]
                
            if clean_script.endswith("```"):
                clean_script = clean_script[:-3]
            
            clean_script = clean_script.strip()
            
            # Validation and format conversion
            try:
                data = json.loads(clean_script)
                
                # Handle both new format (object with intro_text) and old format (array)
                if isinstance(data, list):
                    # Old format: convert to new format
                    clean_script = json.dumps({
                        "intro_text": "",
                        "segments": data
                    }, ensure_ascii=False)
                elif isinstance(data, dict):
                    # New format: ensure structure is correct
                    if "segments" not in data:
                        # If it's just an object without segments, treat as array item
                        clean_script = json.dumps({
                            "intro_text": data.get("intro_text", ""),
                            "segments": data.get("segments", [data])
                        }, ensure_ascii=False)
                        
            except json.JSONDecodeError as e:
                # Fallback: try to extract json part if mixed with text
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Initial JSON parse failed: {e}")
                logger.warning(f"Raw content (first 500 chars): {clean_script[:500]}")
                
                start = clean_script.find('{')
                end = clean_script.rfind('}')
                if start != -1 and end != -1 and end > start:
                    json_part = clean_script[start:end+1]
                    try:
                        # Validate the extracted JSON
                        extracted_data = json.loads(json_part)
                        # Re-serialize to ensure clean format
                        if isinstance(extracted_data, dict) and "segments" in extracted_data:
                            clean_script = json.dumps(extracted_data, ensure_ascii=False)
                            logger.info("Successfully extracted and validated JSON object")
                        else:
                            logger.warning("Extracted JSON doesn't have segments, returning as-is")
                            clean_script = json_part
                    except json.JSONDecodeError as e2:
                        logger.warning(f"Extracted JSON also invalid: {e2}")
                        # Try array format
                        start = clean_script.find('[')
                        end = clean_script.rfind(']')
                        if start != -1 and end != -1:
                            array_part = clean_script[start:end+1]
                            try:
                                segments = json.loads(array_part)
                                clean_script = json.dumps({
                                    "intro_text": "",
                                    "segments": segments
                                }, ensure_ascii=False)
                                logger.info("Successfully extracted array format and converted")
                            except json.JSONDecodeError:
                                logger.error("All JSON extraction attempts failed, returning empty structure")
                                clean_script = json.dumps({
                                    "intro_text": "",
                                    "segments": []
                                }, ensure_ascii=False)
                else:
                    # Try array format as last resort
                    start = clean_script.find('[')
                    end = clean_script.rfind(']')
                    if start != -1 and end != -1:
                        array_part = clean_script[start:end+1]
                        try:
                            segments = json.loads(array_part)
                            clean_script = json.dumps({
                                "intro_text": "",
                                "segments": segments
                            }, ensure_ascii=False)
                        except json.JSONDecodeError:
                            logger.error("Cannot extract valid JSON, returning empty structure")
                            clean_script = json.dumps({
                                "intro_text": "",
                                "segments": []
                            }, ensure_ascii=False)
                    else:
                        logger.error("No JSON structure found, returning empty structure")
                        clean_script = json.dumps({
                            "intro_text": "",
                            "segments": []
                        }, ensure_ascii=False)
            
            return clean_script
        else:
            raise Exception(f"Script generation failed: {response.message}")
