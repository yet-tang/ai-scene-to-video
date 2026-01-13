"""
统一大模型调用配置层

基于LiteLLM实现多模型统一调用，支持：
- 阿里云通义千问（DashScope）
- X.AI Grok
- Anthropic Claude
- OpenAI GPT
- 火山引擎豆包（Volcengine Doubao）

设计文档参考：.qoder/quests/ai-video-editing-system-design.md 第2.2节
"""

from dataclasses import dataclass
import os
from typing import Optional

@dataclass
class ModelConfig:
    """
    大模型配置类
    
    Attributes:
        provider: 提供商标识（dashscope, openai, anthropic, xai）
        model: 模型名称
        api_key_env: 环境变量名称（用于读取API Key）
        temperature: 默认温度参数
        max_tokens: 默认最大token数
        fallback_model: 备用模型（失败时自动切换）
    """
    provider: str
    model: str
    api_key_env: str
    temperature: float = 0.7
    max_tokens: int = 4000
    fallback_model: Optional[str] = None


# ============================================
# Agent模型映射配置
# ============================================

AGENT_MODEL_MAPPING = {
    # 视频分析Agent：使用Qwen-VL-Max（多模态视觉理解）
    "vision_agent": ModelConfig(
        provider="dashscope",
        model="qwen-vl-max",
        api_key_env="DASHSCOPE_API_KEY",
        temperature=0.5,  # 视觉分析需要稳定性
        max_tokens=4000,
    ),
    
    # 卖点提炼Agent：使用Grok（营销创意能力强）
    "selling_point_agent": ModelConfig(
        provider="xai",
        model="grok-4-1-fast-reasoning",
        api_key_env="GROK_API_KEY",
        temperature=0.8,  # 营销文案需要创意
        max_tokens=3000,
        fallback_model="qwen-plus"
    ),
    
    # 脚本创作Agent：使用豆包（高质量文案生成）
    "script_agent": ModelConfig(
        provider="volcengine",
        model="doubao-seed-1-8-251228",
        api_key_env="VOLCENGINE_API_KEY",
        temperature=0.7,
        max_tokens=4000,
        fallback_model="qwen-plus"
    ),
    
    # 智能剪辑Agent：使用Qwen-Plus（决策逻辑）
    "editing_agent": ModelConfig(
        provider="dashscope",
        model="qwen-plus",
        api_key_env="DASHSCOPE_API_KEY",
        temperature=0.6,
        max_tokens=3000,
    ),
    
    # 音频编排Agent：使用Qwen-Plus（实用功能）
    "audio_agent": ModelConfig(
        provider="dashscope",
        model="qwen-plus",
        api_key_env="DASHSCOPE_API_KEY",
        temperature=0.6,
        max_tokens=2000,
    ),
    
    # 视觉增强Agent：使用Qwen-Plus（标注决策）
    "visual_agent": ModelConfig(
        provider="dashscope",
        model="qwen-plus",
        api_key_env="DASHSCOPE_API_KEY",
        temperature=0.5,
        max_tokens=2000,
    ),
    
    # 总导演Agent：使用Qwen-Max（全局协调）
    "orchestrator_agent": ModelConfig(
        provider="dashscope",
        model="qwen-max",
        api_key_env="DASHSCOPE_API_KEY",
        temperature=0.7,
        max_tokens=3000,
    ),
}


# ============================================
# 成本控制策略配置
# ============================================

COST_AWARE_ROUTING = {
    # 是否启用成本感知路由
    "enabled": os.getenv("LLM_COST_AWARE_ROUTING", "true").lower() in {"1", "true", "yes", "y"},
    
    # 高峰时段（工作时间）自动降级到便宜模型
    "high_traffic_hours": [9, 10, 11, 14, 15, 16, 17],
    
    # 降级策略：high_traffic_hours期间强制使用Qwen系列
    "fallback_strategy": "always_use_qwen",  # 或 "none"
}


# ============================================
# 重试策略配置
# ============================================

RETRY_CONFIG = {
    "max_retries": int(os.getenv("LLM_MAX_RETRIES", "3")),
    "retry_delay": float(os.getenv("LLM_RETRY_DELAY", "1.0")),  # 秒
}


# ============================================
# LiteLLM模型前缀映射
# ============================================

PROVIDER_MODEL_PREFIX = {
    # LiteLLM自动识别的模型前缀
    "dashscope": "dashscope/",  # 阿里云通义千问
    "openai": "",  # OpenAI不需要前缀（默认）
    "anthropic": "",  # Claude不需要前缀（自动识别）
    "xai": "",  # Grok不需要前缀（自动识别）
    "gemini": "gemini/",  # Google Gemini
    "volcengine": "volcengine/",  # 火山引擎豆包
}


def get_full_model_name(config: ModelConfig) -> str:
    """
    获取完整的模型名称（包含提供商前缀）
    
    Args:
        config: 模型配置对象
    
    Returns:
        完整模型名称，如 "dashscope/qwen-vl-max"
    """
    prefix = PROVIDER_MODEL_PREFIX.get(config.provider, "")
    return f"{prefix}{config.model}"


def validate_api_keys() -> dict:
    """
    验证所有配置的API Keys是否已设置
    
    Returns:
        验证结果字典 {agent_name: bool}
    """
    results = {}
    for agent_name, config in AGENT_MODEL_MAPPING.items():
        api_key = os.getenv(config.api_key_env)
        results[agent_name] = bool(api_key)
    
    return results
