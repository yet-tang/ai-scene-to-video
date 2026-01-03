import cv2
import numpy as np
from dashscope import MultiModalConversation
from http import HTTPStatus
from config import Config
import tempfile
import os
try:
    from scenedetect import SceneManager, open_video, ContentDetector
except ImportError:
    SceneManager = None

class SceneDetector:
    def __init__(self):
        # Ensure API Key is set
        if not Config.DASHSCOPE_API_KEY:
            raise ValueError("DASHSCOPE_API_KEY is not set")
        
    def detect_video_shots(self, video_path: str, threshold: float = 27.0) -> list[tuple[float, float]]:
        """
        Detect shot boundaries (cuts) in a video using PySceneDetect.
        Returns a list of (start_time, end_time) tuples in seconds.
        """
        if SceneManager is None:
            raise ImportError("scenedetect not installed. Please install scenedetect[opencv]")

        video = open_video(video_path)
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector(threshold=threshold))
        
        # Detect scenes
        scene_manager.detect_scenes(video)
        
        # Get list of scenes (start, end)
        scene_list = scene_manager.get_scene_list()
        
        # Convert FrameTimecodes to seconds
        shots = []
        for scene in scene_list:
            start_sec = scene[0].get_seconds()
            end_sec = scene[1].get_seconds()
            shots.append((start_sec, end_sec))
            
        return shots

    def analyze_shot_grouping(self, shot_frames: list[dict]) -> str:
        """
        Group shots into semantic scenes using Qwen-VL.
        shot_frames: List of {"start": float, "end": float, "image": "path/to/img"}
        """
        prompt = """
        这是一组连续的视频镜头关键帧，每个镜头都有时间范围。
        任务：请分析这些画面，将属于同一场景（例如同一个客厅的不同角度、同一房间的连续镜头）的镜头合并。
        1. 合并相邻且语义相同的镜头。
        2. 识别合并后的场景类型（仅限：小区门头, 小区环境, 客厅, 餐厅, 厨房, 卧室, 卫生间, 阳台, 走廊, 其他）。
        3. 描述该场景的关键特征。
        
        请以 JSON 格式返回合并后的分段列表：
        {
          "segments": [
            {
              "start_sec": 0.0,
              "end_sec": 12.5,
              "scene": "客厅",
              "features": "采光好，大落地窗",
              "score": 0.95
            }
          ]
        }
        """
        
        content = []
        for shot in shot_frames:
            content.append({
                "image": f"file://{shot['image']}"
            })
            content.append({
                "text": f"镜头时间: {shot['start']:.1f}s - {shot['end']:.1f}s"
            })
            
        content.append({"text": prompt})
        
        messages = [{"role": "user", "content": content}]
        
        try:
            # Use Qwen-VL-Plus/Max for better multi-image reasoning
            response = MultiModalConversation.call(model=Config.QWEN_IMAGE_MODEL, messages=messages)
        finally:
            # Cleanup is handled by caller or we can do it here if we want to be safe, 
            # but caller might want to keep images for debugging. 
            # Let's assume caller cleans up.
            pass

        if response.status_code == HTTPStatus.OK:
            return self._content_to_text(response.output.choices[0].message.content)
        else:
            raise Exception(f"Model call failed: {response.message}")

    def _content_to_text(self, content) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    if "text" in item and isinstance(item["text"], str):
                        parts.append(item["text"])
            return "\n".join([p for p in parts if p]).strip()
        if isinstance(content, dict):
            if "text" in content and isinstance(content["text"], str):
                return content["text"]
        return str(content)
        
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

    def extract_key_frames(self, video_url: str, num_frames: int = 5) -> list[str]:
        cap = cv2.VideoCapture(video_url)
        if not cap.isOpened():
            raise Exception(f"Could not open video: {video_url}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            raise Exception("Failed to read total frames")

        num_frames = max(1, int(num_frames))
        if num_frames == 1:
            indices = [total_frames // 2]
        else:
            start = int(total_frames * 0.1)
            end = int(total_frames * 0.9)
            if end <= start:
                start, end = 0, total_frames - 1
            indices = np.linspace(start, end, num_frames).astype(int).tolist()

        paths: list[str] = []
        max_dim = 1024
        try:
            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
                ret, frame = cap.read()
                if not ret:
                    continue
                height, width = frame.shape[:2]
                if width > max_dim or height > max_dim:
                    scaling_factor = max_dim / float(max(width, height))
                    frame = cv2.resize(frame, None, fx=scaling_factor, fy=scaling_factor, interpolation=cv2.INTER_AREA)
                temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                cv2.imwrite(temp_file.name, frame)
                paths.append(temp_file.name)
        finally:
            cap.release()

        if not paths:
            raise Exception("Failed to extract any key frames")
        return paths

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

        response = MultiModalConversation.call(model=Config.QWEN_IMAGE_MODEL, messages=messages)

        # Clean up temp file
        os.remove(image_path)

        if response.status_code == HTTPStatus.OK:
            return self._content_to_text(response.output.choices[0].message.content)
        else:
            raise Exception(f"Model call failed: {response.message}")

    def analyze_scene_from_frames(self, image_paths: list[str]) -> str:
        prompt = """
        你将看到同一段房产视频的不同时刻截图（多张）。
        1. 识别该片段的主场景类型（仅限以下选项：小区门头, 小区环境, 客厅, 餐厅, 厨房, 卧室, 卫生间, 阳台, 走廊）。
        2. 给出画面关键特征（尽量客观、可见）。
        3. 如果多张截图出现明显“场景切换”，请说明但仍返回一个主场景。

        只返回 JSON（不要 markdown）：
        {
          "scene": "场景类型",
          "features": "关键特征描述",
          "score": 0.95
        }
        """

        content = [{"image": f"file://{p}"} for p in image_paths]
        content.append({"text": prompt})
        messages = [{"role": "user", "content": content}]

        try:
            response = MultiModalConversation.call(model=Config.QWEN_IMAGE_MODEL, messages=messages)
        finally:
            for p in image_paths:
                try:
                    os.remove(p)
                except Exception:
                    pass

        if response.status_code == HTTPStatus.OK:
            return self._content_to_text(response.output.choices[0].message.content)
        raise Exception(f"Model call failed: {response.message}")

    def analyze_video_segments(self, video_url: str, max_segments: int = 12) -> str:
        prompt = f"""
        你将看到一段房产视频。请完成“智能分段”：
        - 按内容语义切分成若干连续片段，每个片段尽量对应一个房间/场景。
        - 对每个片段输出：start_sec, end_sec, scene（仅限：小区门头, 小区环境, 客厅, 餐厅, 厨房, 卧室, 卫生间, 阳台, 走廊, 其他）, features, score(0-1)。
        - 片段需按时间顺序、且互不重叠；end_sec > start_sec；尽量覆盖整个视频。
        - 片段数不超过 {int(max_segments)}。

        只返回 JSON（不要 markdown）：
        {{
          "segments": [
            {{"start_sec": 0.0, "end_sec": 5.0, "scene": "小区门头", "features": "...", "score": 0.8}}
          ]
        }}
        """

        messages = [
            {
                "role": "user",
                "content": [
                    {"video": video_url, "fps": Config.QWEN_VIDEO_FPS},
                    {"text": prompt},
                ],
            }
        ]

        response = MultiModalConversation.call(model=Config.QWEN_VIDEO_MODEL, messages=messages)
        if response.status_code == HTTPStatus.OK:
            return self._content_to_text(response.output.choices[0].message.content)
        raise Exception(f"Model call failed: {response.message}")
