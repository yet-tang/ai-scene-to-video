import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Redis (Self-hosted)
    REDIS_URL = os.getenv("REDIS_URL")

    # DashScope (Aliyun Qwen-VL)
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
    QWEN_IMAGE_MODEL = os.getenv("QWEN_IMAGE_MODEL", "qwen-vl-plus")
    QWEN_VIDEO_MODEL = os.getenv("QWEN_VIDEO_MODEL", "qwen-vl-max")
    QWEN_VIDEO_FPS = float(os.getenv("QWEN_VIDEO_FPS", "1.0"))

    # DB (Self-hosted Postgres)
    DB_DSN = os.getenv("DB_DSN")

    # S3 Storage (Cloudflare R2 / AWS S3)
    S3_STORAGE_REGION = os.getenv("S3_STORAGE_REGION", "auto")
    S3_STORAGE_ENDPOINT = os.getenv("S3_STORAGE_ENDPOINT")
    S3_STORAGE_ACCESS_KEY = os.getenv("S3_STORAGE_ACCESS_KEY")
    S3_STORAGE_SECRET_KEY = os.getenv("S3_STORAGE_SECRET_KEY")
    S3_STORAGE_BUCKET = os.getenv("S3_STORAGE_BUCKET", "ai-scene-assets")
    S3_STORAGE_PUBLIC_URL = os.getenv("S3_STORAGE_PUBLIC_URL")

    LOCAL_ASSET_HTTP_BASE_URL = os.getenv("LOCAL_ASSET_HTTP_BASE_URL", "http://ai-scene-backend:8090/public")

    SMART_SPLIT_ENABLED = os.getenv("SMART_SPLIT_ENABLED", "true").lower() in {"1", "true", "yes", "y"}
    SMART_SPLIT_STRATEGY = os.getenv("SMART_SPLIT_STRATEGY", "hybrid")
    SMART_SPLIT_MIN_DURATION_SEC = float(os.getenv("SMART_SPLIT_MIN_DURATION_SEC", "30"))
    SCENE_DETECT_THRESHOLD = float(os.getenv("SCENE_DETECT_THRESHOLD", "27.0"))
