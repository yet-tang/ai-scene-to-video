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
        Returns a JSON string of list[dict] structure: [{"asset_id": "...", "text": "..."}]
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
你是一位专业的房产短视频解说达人。你的声音将被直接录制。

# Context Data
{context_str}

# Task
根据视频片段顺序，撰写**严格对应**的口语解说词。

# Critical Constraints (MUST FOLLOW)
1. **结构化输出**: 必须返回一个 JSON 数组，格式为：
   ```json
   [
     {{"asset_id": "片段ID", "text": "解说词内容..."}},
     ...
   ]
   ```
   **不要**改变 ID，必须原样返回。

2. **时长预算 (Time Budget)**:
   - 必须严格遵守每个片段的“建议字数”。
   - 如果画面只有 3 秒，解说词必须非常简短（如“看这大窗户”），切勿长篇大论。
   - 语速控制在每秒 4 字左右。

3. **视觉锚定**: 解说内容必须与画面场景实时对应。

4. **口语拟真**:
   - 杭州本地口语风格（儿化音、语气词）。
   - 自然、真诚，像朋友聊天。
   - 拒绝书面语，拒绝销售套话。

# Output Example
```json
[
  {{"asset_id": "uuid-1", "text": "哎，今儿带你们看个特别逗的房子..."}},
  {{"asset_id": "uuid-2", "text": "进门这个玄关，说实话，有点窄。"}}
]
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
            
            # Validation
            try:
                json.loads(clean_script)
            except json.JSONDecodeError:
                # Fallback: try to extract json part if mixed with text
                start = clean_script.find('[')
                end = clean_script.rfind(']')
                if start != -1 and end != -1:
                    clean_script = clean_script[start:end+1]
            
            return clean_script
        else:
            raise Exception(f"Script generation failed: {response.message}")
