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

    # S3 / Supabase Storage
    SUPABASE_STORAGE_REGION = os.getenv("SUPABASE_STORAGE_REGION", "us-east-1")
    SUPABASE_STORAGE_ENDPOINT = os.getenv("SUPABASE_STORAGE_ENDPOINT")
    SUPABASE_STORAGE_ACCESS_KEY = os.getenv("SUPABASE_STORAGE_ACCESS_KEY")
    SUPABASE_STORAGE_SECRET_KEY = os.getenv("SUPABASE_STORAGE_SECRET_KEY")
    SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "ai-scene-assets")
    SUPABASE_STORAGE_PUBLIC_URL = os.getenv("SUPABASE_STORAGE_PUBLIC_URL")
