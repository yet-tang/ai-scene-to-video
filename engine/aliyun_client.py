import time
import logging
import json
import urllib.request
from urllib.error import HTTPError, URLError
from typing import Optional, Dict, Any
from config import Config

logger = logging.getLogger(__name__)

class AliyunClient:
    """
    Client for Aliyun Wanxiang (Tongyi Wanxiang) Video Generation & Editing APIs.
    """
    
    BASE_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"
    
    def __init__(self):
        self.api_key = Config.DASHSCOPE_API_KEY
        if not self.api_key:
            logger.warning("DASHSCOPE_API_KEY is not set. AliyunClient will not function.")
            
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"
        }
    
    def _request_json(self, url: str, *, method: str, headers: Dict[str, str], body: Optional[Dict[str, Any]] = None, timeout: int = 30) -> Dict[str, Any]:
        data_bytes = None
        if body is not None:
            data_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            if not raw:
                return {}
            return json.loads(raw.decode("utf-8"))
        except HTTPError as e:
            raise RuntimeError(f"Aliyun API HTTPError: {e.code}") from e
        except URLError as e:
            raise RuntimeError("Aliyun API URLError") from e
        except Exception as e:
            raise RuntimeError("Aliyun API request failed") from e

    def submit_task(self, model: str, input_data: Dict[str, Any], parameters: Optional[Dict[str, Any]] = None) -> str:
        """
        Submit an async task to Aliyun Video Synthesis API.
        Returns: task_id (str)
        """
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY is missing")

        payload = {
            "model": model,
            "input": input_data,
            "parameters": parameters or {}
        }

        logger.info(f"Submitting Aliyun task with model={model}")
        data = self._request_json(self.BASE_URL, method="POST", headers=self._get_headers(), body=payload, timeout=30)
        task_id = (data.get("output") or {}).get("task_id")
        if not task_id:
            raise ValueError("No task_id in response")
        logger.info(f"Task submitted successfully. Task ID: {task_id}")
        return task_id

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Check the status of a submitted task.
        """
        url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        return self._request_json(url, method="GET", headers=headers, body=None, timeout=10)

    def wait_for_task(self, task_id: str, timeout: int = 600, check_interval: int = 10) -> Optional[Dict[str, Any]]:
        """
        Poll task status until success or failure.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            data = self.get_task_status(task_id)
            output = data.get("output", {})
            status = output.get("task_status", "").upper()
            
            if status == "SUCCEEDED":
                logger.info(f"Task {task_id} succeeded.")
                return output
            elif status in ["FAILED", "CANCELED"]:
                code = output.get("code")
                message = output.get("message")
                logger.error(f"Task {task_id} failed: {code} - {message}")
                raise RuntimeError(f"Aliyun task failed: {message}")
            elif status in ["PENDING", "RUNNING"]:
                logger.debug(f"Task {task_id} is {status}...")
                time.sleep(check_interval)
            else:
                logger.warning(f"Unknown task status: {status}")
                time.sleep(check_interval)
                
        raise TimeoutError(f"Task {task_id} timed out after {timeout} seconds")

    # --- Convenience Methods for Specific Capabilities ---

    def video_repainting(self, video_url: str, prompt: str, control_condition: str = "depth") -> str:
        """
        Apply video repainting (style transfer/editing).
        """
        input_data = {
            "function": "video_repainting",
            "prompt": prompt,
            "video_url": video_url
        }
        # Note: prompt_extend=False helps stick to the specific style instruction
        params = {
            "prompt_extend": False, 
            "control_condition": control_condition
        }
        
        task_id = self.submit_task("wanx2.1-vace-plus", input_data, params)
        result = self.wait_for_task(task_id)
        
        # Extract video URL from result
        # Typically result['video_url'] or result['results'][0]['url']
        video_url = result.get("video_url")
        if not video_url and result.get("results"):
             video_url = result["results"][0].get("url")
             
        if not video_url:
            raise RuntimeError("No video URL found in successful task result")
            
        return video_url

    def image_to_video(self, image_url: str, prompt: str) -> str:
        raise NotImplementedError("基于现有知识，我无法确定该图生视频接口参数，请查阅最新官方文档。")
