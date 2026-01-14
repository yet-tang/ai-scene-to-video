import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Redis (Self-hosted)
    REDIS_URL = os.getenv("REDIS_URL")

    CELERY_QUEUE_NAME = os.getenv("CELERY_QUEUE_NAME", "ai-video:celery")

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

    TTS_ENGINE = os.getenv("TTS_ENGINE", "cosyvoice").lower()
    _DEFAULT_TTS_MODEL = "cosyvoice-v3-flash" if TTS_ENGINE in {"cosyvoice", "tts_v2"} else "sambert-zhigui-v1"
    TTS_MODEL = os.getenv("TTS_MODEL", _DEFAULT_TTS_MODEL)
    TTS_VOICE = os.getenv("TTS_VOICE", "longanyang")
    _TTS_ENABLE_SSML_RAW = os.getenv("TTS_ENABLE_SSML", "")
    TTS_ENABLE_SSML = (_TTS_ENABLE_SSML_RAW.lower() in {"1", "true", "yes", "y"}) if _TTS_ENABLE_SSML_RAW else (TTS_ENGINE in {"cosyvoice", "tts_v2"})
    TTS_VOLUME = int(os.getenv("TTS_VOLUME", "50"))
    TTS_SPEECH_RATE = float(os.getenv("TTS_SPEECH_RATE", "1.0"))
    TTS_PITCH_RATE = float(os.getenv("TTS_PITCH_RATE", "1.0"))

    # Subtitle Configuration (P0 Feature)
    SUBTITLE_ENABLED = os.getenv("SUBTITLE_ENABLED", "true").lower() in {"1", "true", "yes", "y"}
    
    # Font Management (Extensible)
    # Built-in fonts available in container:
    # - Noto-Sans-CJK-SC-Bold: System font (via fonts-noto-cjk package)
    # - AlibabaPuHuiTi-3-75-SemiBold: Custom font from /app/assets/fonts
    AVAILABLE_FONTS = {
        "noto-sans-bold": "Noto-Sans-CJK-SC-Bold",  # System font (default)
        "alibaba-puhuiti-semibold": "AlibabaPuHuiTi-3-75-SemiBold",  # Custom font
        # Future: Add more fonts here
    }
    
    # Default font selection (can be overridden via SUBTITLE_FONT env var)
    _FONT_KEY = os.getenv("SUBTITLE_FONT_KEY", "alibaba-puhuiti-semibold")  # Font key from AVAILABLE_FONTS
    _FONT_NAME_OVERRIDE = os.getenv("SUBTITLE_FONT", "")  # Direct font name override
    SUBTITLE_FONT = _FONT_NAME_OVERRIDE if _FONT_NAME_OVERRIDE else AVAILABLE_FONTS.get(_FONT_KEY, "Noto-Sans-CJK-SC-Bold")
    
    SUBTITLE_FONT_SIZE = int(os.getenv("SUBTITLE_FONT_SIZE", "48"))
    SUBTITLE_POSITION = float(os.getenv("SUBTITLE_POSITION", "0.75"))  # 0-1, relative to screen height

    # Visual Enhancement Configuration (P0 Feature)
    VISUAL_ENHANCEMENT_ENABLED = os.getenv("VISUAL_ENHANCEMENT_ENABLED", "true").lower() in {"1", "true", "yes", "y"}
    VISUAL_ENHANCEMENT_STRATEGY = os.getenv("VISUAL_ENHANCEMENT_STRATEGY", "smart")  # "all", "smart", "none"
    VISUAL_ENHANCEMENT_MODEL = os.getenv("VISUAL_ENHANCEMENT_MODEL", "wanx2.1-vace-plus")

    # SFX Configuration (P1 Feature)
    SFX_ENABLED = os.getenv("SFX_ENABLED", "false").lower() in {"1", "true", "yes", "y"}
    SFX_LIBRARY_PATH = os.getenv("SFX_LIBRARY_PATH", "/app/sfx_library")  # Path to sound effects library

    # Audio Mixing Configuration (P1 Feature)
    AUTO_DUCKING_ENABLED = os.getenv("AUTO_DUCKING_ENABLED", "false").lower() in {"1", "true", "yes", "y"}
    BGM_VOLUME = float(os.getenv("BGM_VOLUME", "0.15"))  # Default 15%
    BGM_DUCKING_LEVEL = float(os.getenv("BGM_DUCKING_LEVEL", "0.3"))  # Duck to 30% during TTS

    # Subtitle Style (Advanced)
    SUBTITLE_STYLE = os.getenv("SUBTITLE_STYLE", "default")  # Options: default, elegant, bold
    
    # Intro/Outro Card Configuration
    INTRO_ENABLED = os.getenv("INTRO_ENABLED", "true").lower() in {"1", "true", "yes", "y"}
    OUTRO_ENABLED = os.getenv("OUTRO_ENABLED", "true").lower() in {"1", "true", "yes", "y"}
    INTRO_DURATION = float(os.getenv("INTRO_DURATION", "3.0"))  # Seconds (fallback if no voice)
    OUTRO_DURATION = float(os.getenv("OUTRO_DURATION", "3.0"))  # Seconds
    
    # Intro Voice Configuration (开场白语音)
    INTRO_VOICE_ENABLED = os.getenv("INTRO_VOICE_ENABLED", "true").lower() in {"1", "true", "yes", "y"}
    INTRO_USE_FIRST_VIDEO = os.getenv("INTRO_USE_FIRST_VIDEO", "true").lower() in {"1", "true", "yes", "y"}  # Use first video as intro background

    # Performance Optimization
    RENDER_THREADS = int(os.getenv("RENDER_THREADS", "4"))  # FFmpeg rendering threads
    ENABLE_CLIP_CACHE = os.getenv("ENABLE_CLIP_CACHE", "false").lower() in {"1", "true", "yes", "y"}
    MAX_VIDEO_RESOLUTION = int(os.getenv("MAX_VIDEO_RESOLUTION", "1080"))  # Max height in pixels

    # ============ Phase 2-1: 动态节奏控制 ============
    DYNAMIC_SPEED_ENABLED = os.getenv("DYNAMIC_SPEED_ENABLED", "true").lower() in {"1", "true", "yes", "y"}
    
    # 速度映射配置（可通过环境变量覆盖）
    SPEED_MAP_STUNNING = float(os.getenv("SPEED_MAP_STUNNING", "0.85"))  # 惊艳镜头
    SPEED_MAP_HEALING = float(os.getenv("SPEED_MAP_HEALING", "0.90"))   # 治愈镜头
    SPEED_MAP_COZY = float(os.getenv("SPEED_MAP_COZY", "0.90"))        # 温馨镜头
    SPEED_MAP_LUXURY = float(os.getenv("SPEED_MAP_LUXURY", "0.95"))    # 高级镜头
    SPEED_MAP_NORMAL = float(os.getenv("SPEED_MAP_NORMAL", "1.0"))     # 普通镜头
    SPEED_MAP_TRANSITION = float(os.getenv("SPEED_MAP_TRANSITION", "1.1"))  # 过渡镜头
    
    # ============ Phase 2-2: BGM智能匹配 ============
    BGM_AUTO_SELECT_ENABLED = os.getenv("BGM_AUTO_SELECT_ENABLED", "false").lower() in {"1", "true", "yes", "y"}
    BGM_DYNAMIC_VOLUME_ENABLED = os.getenv("BGM_DYNAMIC_VOLUME_ENABLED", "true").lower() in {"1", "true", "yes", "y"}
    BGM_LIBRARY_PATH = os.getenv("BGM_LIBRARY_PATH", "/app/bgm_library.json")
    
    # ============ Phase 2-3: 多智能体协作 ============
    MULTI_AGENT_ENABLED = os.getenv("MULTI_AGENT_ENABLED", "true").lower() in {"1", "true", "yes", "y"}
    MULTI_AGENT_MAX_ITERATIONS = int(os.getenv("MULTI_AGENT_MAX_ITERATIONS", "3"))  # 最大迭代次数
    MULTI_AGENT_QUALITY_THRESHOLD = float(os.getenv("MULTI_AGENT_QUALITY_THRESHOLD", "80"))  # 质量合格阈值

    @classmethod
    def validate(cls):
        """\n        Validate critical configuration and log warnings.\n        """
        logger = logging.getLogger(__name__)
        
        issues = []
        
        # Check critical API keys
        if not cls.DASHSCOPE_API_KEY:
            issues.append("DASHSCOPE_API_KEY not set - AI features will not work")
        
        # Check database
        if not cls.DB_DSN:
            issues.append("DB_DSN not set - database operations will fail")
        
        # Check S3 storage
        if not cls.S3_STORAGE_ENDPOINT or not cls.S3_STORAGE_ACCESS_KEY:
            issues.append("S3 storage not fully configured - file uploads may fail")
        
        # Validate feature dependencies
        if cls.VISUAL_ENHANCEMENT_ENABLED and not cls.DASHSCOPE_API_KEY:
            issues.append("VISUAL_ENHANCEMENT_ENABLED but DASHSCOPE_API_KEY missing")
        
        if cls.SFX_ENABLED:
            if not os.path.exists(cls.SFX_LIBRARY_PATH):
                issues.append(f"SFX_ENABLED but library path not found: {cls.SFX_LIBRARY_PATH}")
        
        # Validate font configuration
        if cls.SUBTITLE_ENABLED:
            font_name = cls.SUBTITLE_FONT
            logger.info(f"Subtitle font configured: {font_name}")
            # Check if custom fonts directory exists
            custom_font_dir = "/app/assets/fonts"
            if os.path.exists(custom_font_dir):
                font_files = os.listdir(custom_font_dir)
                logger.info(f"Custom fonts available: {', '.join(font_files)}")
            else:
                logger.debug(f"Custom font directory not found: {custom_font_dir}")
        
        # Log all issues
        for issue in issues:
            logger.warning(f"Config validation: {issue}")
        
        return len(issues) == 0
