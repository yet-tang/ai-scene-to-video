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
        你是一个专业的房产短视频脚本编剧。请根据以下房源信息和视频画面顺序，撰写一段吸引人的口播解说词。
        
        {context_str}

        要求：
        1. 语气热情、专业、有感染力。
        2. 严格按照视频片段的顺序来写，确保画音同步。
        3. 总时长控制在45-60秒左右（约200-250字）。
        4. 不需要分镜头描述，只需要输出纯文本的解说词内容。
        5. 开头要有吸引力，结尾要有引导（如“欢迎预约看房”）。
        """

        messages = [
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': prompt}
        ]

        # 3. Call Qwen-Plus
        response = Generation.call(model='qwen-plus',
                                   messages=messages,
                                   result_format='message')

        if response.status_code == HTTPStatus.OK:
            return response.output.choices[0].message.content
        else:
            raise Exception(f"Script generation failed: {response.message}")
