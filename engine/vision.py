import cv2
import numpy as np
from dashscope import MultiModalConversation
from http import HTTPStatus
from config import Config
import tempfile
import os

class SceneDetector:
    def __init__(self):
        # Ensure API Key is set
        if not Config.DASHSCOPE_API_KEY:
            raise ValueError("DASHSCOPE_API_KEY is not set")
        
    def extract_key_frame(self, video_url: str) -> str:
        """
        Download video from URL (or read local), extract the middle frame, 
        save as temp file, and return path.
        """
        # OpenCV can read directly from URL usually, but it's safer to download if needed.
        # For now, let's try reading directly.
        cap = cv2.VideoCapture(video_url)
        
        if not cap.isOpened():
            raise Exception(f"Could not open video: {video_url}")

        # Get total frames
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Jump to middle frame
        middle_frame_index = total_frames // 2
        cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame_index)
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise Exception("Failed to read frame")

        # Resize to reduce upload size (e.g. max 1024px width)
        height, width = frame.shape[:2]
        max_dim = 1024
        if width > max_dim or height > max_dim:
            scaling_factor = max_dim / float(max(width, height))
            frame = cv2.resize(frame, None, fx=scaling_factor, fy=scaling_factor, interpolation=cv2.INTER_AREA)

        # Save to temp file
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        cv2.imwrite(temp_file.name, frame)
        return temp_file.name

    def analyze_scene(self, image_path: str):
        """
        Call Qwen-VL-Plus to analyze the image.
        """
        # Qwen-VL prompt engineering
        prompt = """
        请分析这张图片，它是房产视频的一个截图。
        1. 识别场景类型（仅限以下选项：小区门头, 小区环境, 客厅, 餐厅, 厨房, 卧室, 卫生间, 阳台, 走廊）。
        2. 描述画面的关键特征（如采光、装修风格、整洁度），用于生成解说词。
        3. 如果画面模糊或无法识别，请说明。
        
        请以JSON格式返回：
        {
            "scene": "场景类型",
            "features": "关键特征描述",
            "score": 0.95 (置信度预估，0-1)
        }
        """

        messages = [
            {
                "role": "user",
                "content": [
                    {"image": f"file://{image_path}"},
                    {"text": prompt}
                ]
            }
        ]

        response = MultiModalConversation.call(model='qwen-vl-plus', messages=messages)

        # Clean up temp file
        os.remove(image_path)

        if response.status_code == HTTPStatus.OK:
            return response.output.choices[0].message.content
        else:
            raise Exception(f"Model call failed: {response.message}")
