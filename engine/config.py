import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import urllib.parse

class Config:
    # Redis (Self-hosted)
    REDIS_URL = os.getenv("REDIS_URL", "redis://default:li1MpI70nCT2kj4l7pmW6bpW0Zojmksd4MdSaKSbcw0u3R0iHuc3j2Ek8AyU51a5@w40w8wkgwwsw40c08c0cwg84:6379/0")

    # DashScope (Aliyun Qwen-VL)
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

    # DB (Self-hosted Postgres)
    # Password contains special characters, so we need to URL encode it if it's not already in the DSN
    # Assuming user wants to hardcode this specific password for MVP:
    # Raw Password: %H4L]~vtb7v2ri2F@t~tv4mo9KvLz:+e4Gvr
    # Encoded Password: %25H4L%5D%7Evtb7v2ri2F%40t%7Etv4mo9KvLz%3A%2Be4Gvr
    
    _db_user = "ai_scene_video_user"
    _db_pass = urllib.parse.quote_plus("RyAf43CRcMMe2tGwvzdFxr1YpwiFg9PC16XdMDC9195jMWwU")
    _db_host = "ewo0ccsg04cogsw0ws0wowgw"
    _db_port = "5432"
    _db_name = "ai_scene_video_service"

    DB_DSN = os.getenv("DB_DSN", f"postgresql://{_db_user}:{_db_pass}@{_db_host}:{_db_port}/{_db_name}")

    # S3 / Supabase Storage
    SUPABASE_STORAGE_REGION = os.getenv("SUPABASE_STORAGE_REGION", "us-east-1")
    SUPABASE_STORAGE_ENDPOINT = os.getenv("SUPABASE_STORAGE_ENDPOINT")
    SUPABASE_STORAGE_ACCESS_KEY = os.getenv("SUPABASE_STORAGE_ACCESS_KEY")
    SUPABASE_STORAGE_SECRET_KEY = os.getenv("SUPABASE_STORAGE_SECRET_KEY")
    SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "ai-scene-assets")
    SUPABASE_STORAGE_PUBLIC_URL = os.getenv("SUPABASE_STORAGE_PUBLIC_URL")
