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
        context_str = f"房源信息：{json.dumps(house_info, ensure_ascii=False)}\n\n"
        context_str += "视频片段顺序及时长预算：\n"
        
        for idx, item in enumerate(timeline_data):
            scene = item.get('scene_label', '未知场景')
            # features = item.get('scene_score', '') 
            duration = float(item.get('duration', 5.0))
            # Budget: ~4 chars per second
            word_budget = math.floor(duration * 4)
            asset_id = item.get('id') or item.get('asset_id') or 'unknown'
            
            context_str += f"片段{idx+1} [ID: {asset_id}]: {scene} (时长: {duration:.1f}秒, 建议字数: {word_budget}字以内)\n"

        # 2. Prompt Engineering
        prompt = f"""
# Role
你是一位专业的房产短视频解说达人，擅长"温情生活风"文案创作。

# Context Data
{context_str}

# Task
1. 先撰写一段开场白（intro_text），用于视频片头介绍这套房子的基本情况
2. 然后根据视频片段顺序，撰写严格对应的口语解说词

# Style Guidelines ("Warm Life Style")
1.  **情感化**: 从"描述事实"转为"情绪渲染"。强调"治愈"、"阳光"、"家的味道"。
2.  **口语拟真**: 自然真诚，像朋友聊天。
3.  **高级感**: 挖掘房源的独特价值（采光、质感）。

# Critical Constraints (MUST FOLLOW)
1. **结构化输出**: 必须返回一个 JSON 对象，格式如下：
   ```json
   {{
     "intro_text": "开场白文案，30-50字，介绍房源基本信息（小区名、户型、特色等），以问候开头，以引导语结尾",
     "segments": [
       {{
         "asset_id": "片段ID",
         "text": "解说词内容...",
         "visual_prompt": "English prompt for AI video filter",
         "audio_cue": "SFX suggestion"
       }},
       ...
     ]
   }}
   ```
   **不要**改变 asset_id，必须原样返回。

2. **开场白要求 (intro_text)**:
   - 必须以"大家好"或类似的问候开头
   - 必须包含房源的核心信息（位置/小区名、户型、一个亮点）
   - 必须以引导语结束，如"走，进去看看"、"跟我一起感受一下"
   - 控制在 30-50 字，读起来 5-8 秒

3. **时长预算 (Time Budget)**:
   - 必须严格遵守每个片段的"建议字数"。
   - 语速控制在每秒 4 字左右。

4. **视觉锚定**: 解说内容必须与画面场景实时对应。

# Output Example
```json
{{
  "intro_text": "大家好，今天带大家看的这套是位于滨江苑的三居室，采光特别好，还能看到江景。走，进去感受一下！",
  "segments": [
    {{
      "asset_id": "uuid-1",
      "text": "哎，谁能拒绝一个满屋阳光的客厅呢？这种透明感，真的住进去就不想出门。",
      "visual_prompt": "Bright living room, sunlight streaming through sheer curtains, warm golden hour lighting, 4k, cozy atmosphere",
      "audio_cue": "Soft morning jazz music"
    }},
    {{
      "asset_id": "uuid-2",
      "text": "走上这几级台阶，满满的仪式感。独立的衣帽间，藏着你所有的精致。",
      "visual_prompt": "Walk-in closet, elegant lighting, wooden texture, high resolution",
      "audio_cue": "Footsteps on wood"
    }}
  ]
}}
```

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
                        
            except json.JSONDecodeError:
                # Fallback: try to extract json part if mixed with text
                start = clean_script.find('{')
                end = clean_script.rfind('}')
                if start != -1 and end != -1:
                    clean_script = clean_script[start:end+1]
                else:
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
                        except:
                            pass
            
            return clean_script
        else:
            raise Exception(f"Script generation failed: {response.message}")
