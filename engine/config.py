import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Redis (Self-hosted)
    REDIS_URL = os.getenv("REDIS_URL")

    # DashScope (Aliyun Qwen-VL)
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

    # DB (Self-hosted Postgres)
    DB_DSN = os.getenv("DB_DSN")

    # S3 Storage (Cloudflare R2 / AWS S3)
    S3_STORAGE_REGION = os.getenv("S3_STORAGE_REGION", "auto")
    S3_STORAGE_ENDPOINT = os.getenv("S3_STORAGE_ENDPOINT")
    S3_STORAGE_ACCESS_KEY = os.getenv("S3_STORAGE_ACCESS_KEY")
    S3_STORAGE_SECRET_KEY = os.getenv("S3_STORAGE_SECRET_KEY")
    S3_STORAGE_BUCKET = os.getenv("S3_STORAGE_BUCKET", "ai-scene-assets")
    S3_STORAGE_PUBLIC_URL = os.getenv("S3_STORAGE_PUBLIC_URL")
