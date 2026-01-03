import json
from http import HTTPStatus
from dashscope import Generation
from config import Config

class ScriptGenerator:
    def __init__(self):
        if not Config.DASHSCOPE_API_KEY:
            raise ValueError("DASHSCOPE_API_KEY is not set")

    def generate_script(self, house_info: dict, timeline_data: list) -> str:
        """
        Generate a video script based on house info and ordered asset timeline.
        """
        
        # 1. Build Context
        context_str = f"房源信息：{json.dumps(house_info, ensure_ascii=False)}\n\n"
        context_str += "视频片段顺序及AI分析特征：\n"
        
        for idx, item in enumerate(timeline_data):
            scene = item.get('scene_label', '未知场景')
            features = item.get('scene_score', '') # Actually we stored score, but for MVP let's assume we might pass features if we stored them.
            # In V1 DB schema we didn't store 'features' text in assets table, only label and score.
            # So we rely on label and house info mostly.
            context_str += f"{idx+1}. {scene}\n"

        # 2. Prompt Engineering
        prompt = f"""
# Role
你是一位专业的房产短视频解说达人。你的声音将被直接录制，因此你的输出必须是**纯粹的口语文本**，不能包含任何非朗读内容。

# Context Data
以下是房源信息和视频画面的分镜描述流：
{context_str}

# Task
根据上述房源信息和视频画面顺序，撰写一段连贯、引人入胜的**口语解说词**。

# Critical Constraints (MUST FOLLOW)
1. **格式清洗 (Format Purge)**: 输出结果将被直接发送给 TTS 引擎。**严禁**输出 JSON、Markdown、标题、前缀（如 "Script:"）、分镜标记（如 "[Scene 1]"）或任何非解说词的解释性文字。
2. **纯文本流**: 只输出要朗读的内容本身。
3. **视觉锚定**: 必须严格按照“视频片段顺序”来推进解说。解说内容必须与画面发生的动作实时对应。
4. **口语拟真 (Oral Simulation)**:
    - 拒绝书面语，拒绝销售套话（如“尊贵”、“尽享”）。
    - 像给朋友介绍房子一样，自然、真诚。
    - 适当加入口语填充词（如“那个...”、“哎你看...”、“说实话...”）来增加真实感。
    - 巧妙利用标点符号控制节奏：使用逗号“，”表示短停顿，使用省略号“...”表示观察时的长停顿或悬念。
5. **时长控制**: 45-60秒左右（约200-250字）。

# Tone & Style
- 沉浸感强，像是朋友在耳边低语。
- 情感充沛，不要像机器人一样棒读。

# Output Example (Format Reference ONLY)
(正确): 哎，今儿带你们看个特别逗的房子... 进门这个玄关，说实话，有点窄，但你往里走... 豁！看见没？这大落地窗，直接把我看愣了... 
(错误): Script: 哎，今儿带你们看个特别逗的房子... 
(错误): 大家好，我是AI助手，以下是解说词...

# Action
现在，请直接开始解说，不要说任何废话：
"""

        messages = [
            {'role': 'system', 'content': 'You are a professional video script writer.'},
            {'role': 'user', 'content': prompt}
        ]

        # 3. Call Qwen-Plus
        response = Generation.call(model='qwen-plus',
                                   messages=messages,
                                   result_format='message',
                                   temperature=0.7)  # Increase creativity for colloquial style

        if response.status_code == HTTPStatus.OK:
            content = response.output.choices[0].message.content
            # Post-processing to clean up common artifacts
            clean_script = content.strip().strip('"').strip("'")
            if clean_script.lower().startswith("script:"):
                clean_script = clean_script[7:].strip()
            return clean_script
        else:
            raise Exception(f"Script generation failed: {response.message}")
