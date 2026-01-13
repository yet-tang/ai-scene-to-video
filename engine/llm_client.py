"""
统一大模型调用客户端

基于LiteLLM实现统一的大模型调用接口，屏蔽不同提供商的API差异。

特性：
- 统一OpenAI格式接口
- 自动Fallback到备用模型
- 成本感知路由（高峰期降级）
- 完整的日志记录
- 多模态调用支持

设计文档参考：.qoder/quests/ai-video-editing-system-design.md 第2.2节
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import litellm
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    logging.warning("litellm not installed, unified LLM client will not be available")

from llm_config import (
    AGENT_MODEL_MAPPING,
    COST_AWARE_ROUTING,
    RETRY_CONFIG,
    ModelConfig,
    get_full_model_name,
)

logger = logging.getLogger(__name__)


class UnifiedLLMClient:
    """
    统一大模型调用客户端
    
    使用方式：
    ```python
    # 初始化指定Agent的客户端
    client = UnifiedLLMClient(agent_name="script_agent")
    
    # 文本对话
    response = client.chat([
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': 'Hello!'}
    ])
    
    # 多模态调用
    response = client.multimodal([
        {'type': 'text', 'text': 'Describe this image'},
        {'type': 'image_url', 'image_url': {'url': 'https://...'}}
    ])
    ```
    """
    
    def __init__(self, agent_name: str):
        """
        初始化客户端
        
        Args:
            agent_name: Agent名称，必须在AGENT_MODEL_MAPPING中定义
        
        Raises:
            ValueError: 未知的Agent名称
            ImportError: litellm未安装
        """
        if not LITELLM_AVAILABLE:
            raise ImportError(
                "litellm is required for unified LLM client. "
                "Install with: pip install litellm>=1.50.0"
            )
        
        if agent_name not in AGENT_MODEL_MAPPING:
            raise ValueError(
                f"Unknown agent: {agent_name}. "
                f"Available agents: {list(AGENT_MODEL_MAPPING.keys())}"
            )
        
        self.agent_name = agent_name
        self.config = AGENT_MODEL_MAPPING[agent_name]
        
        # 验证API Key
        api_key = os.getenv(self.config.api_key_env)
        if not api_key:
            logger.warning(
                f"{self.config.api_key_env} not set for {agent_name}, "
                f"will attempt fallback if available"
            )
        
        # LiteLLM全局配置
        litellm.set_verbose = False  # 生产环境关闭详细日志
        litellm.drop_params = True   # 自动过滤不支持的参数
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        统一文本对话接口
        
        Args:
            messages: OpenAI格式的消息列表
                      [{'role': 'system', 'content': '...'}, 
                       {'role': 'user', 'content': '...'}]
            temperature: 温度参数（覆盖配置默认值）
            max_tokens: 最大token数（覆盖配置默认值）
            **kwargs: 其他参数（传递给litellm.completion）
        
        Returns:
            模型回复的文本内容
        
        Raises:
            Exception: API调用失败且无Fallback
        """
        model = self._select_model()
        
        # 准备调用参数
        call_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.config.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.config.max_tokens,
            "api_key": os.getenv(self.config.api_key_env),
        }
        call_params.update(kwargs)
        
        try:
            response = litellm.completion(**call_params)
            
            # 成功日志
            logger.info(
                f"LLM call success",
                extra={
                    "event": "llm.call.success",
                    "agent": self.agent_name,
                    "model": model,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.warning(
                f"LLM call failed: {type(e).__name__}: {str(e)[:200]}",
                extra={
                    "event": "llm.call.failed",
                    "agent": self.agent_name,
                    "model": model,
                    "error_type": type(e).__name__,
                    "error": str(e)[:200]
                }
            )
            
            # 自动降级到备用模型
            if self.config.fallback_model:
                logger.info(f"Attempting fallback to {self.config.fallback_model}")
                return self._call_fallback(messages, temperature, max_tokens, **kwargs)
            
            # 无Fallback，抛出异常
            raise
    
    def multimodal(
        self,
        content: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        多模态调用（支持图片/视频）
        
        Args:
            content: OpenAI格式的多模态内容列表
                     [{'type': 'text', 'text': '...'},
                      {'type': 'image_url', 'image_url': {'url': '...'}}]
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数
        
        Returns:
            模型回复的文本内容
        
        Raises:
            Exception: API调用失败且无Fallback
        """
        model = self._select_model()
        
        # 构建消息格式
        messages = [{'role': 'user', 'content': content}]
        
        call_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.config.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.config.max_tokens,
            "api_key": os.getenv(self.config.api_key_env),
        }
        call_params.update(kwargs)
        
        try:
            response = litellm.completion(**call_params)
            
            logger.info(
                f"Multimodal call success",
                extra={
                    "event": "llm.multimodal.success",
                    "agent": self.agent_name,
                    "model": model,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                }
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(
                f"Multimodal call failed: {type(e).__name__}: {str(e)[:200]}",
                extra={
                    "event": "llm.multimodal.failed",
                    "agent": self.agent_name,
                    "model": model,
                    "error": str(e)[:200]
                }
            )
            
            # 尝试Fallback
            if self.config.fallback_model:
                return self._call_fallback(messages, temperature, max_tokens, **kwargs)
            
            raise
    
    def _select_model(self) -> str:
        """
        智能模型选择（支持成本控制）
        
        成本感知逻辑：
        - 如果启用成本路由且当前为高峰时段，自动降级到便宜模型
        - 否则使用配置的默认模型
        
        Returns:
            完整模型名称（含提供商前缀）
        """
        # 成本控制：高峰期自动降级
        if (
            COST_AWARE_ROUTING.get("enabled", False)
            and COST_AWARE_ROUTING.get("fallback_strategy") == "always_use_qwen"
        ):
            current_hour = datetime.now().hour
            high_traffic_hours = COST_AWARE_ROUTING.get("high_traffic_hours", [])
            
            if current_hour in high_traffic_hours and self.config.fallback_model:
                logger.info(
                    f"High traffic hour ({current_hour}), using fallback model",
                    extra={
                        "event": "llm.cost_aware_routing",
                        "agent": self.agent_name,
                        "original_model": get_full_model_name(self.config),
                        "fallback_model": f"dashscope/{self.config.fallback_model}"
                    }
                )
                return f"dashscope/{self.config.fallback_model}"
        
        # 返回默认模型
        return get_full_model_name(self.config)
    
    def _call_fallback(
        self,
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        备用模型调用
        
        当主模型失败时，自动切换到fallback_model（通常为Qwen系列）
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数
        
        Returns:
            模型回复的文本内容
        
        Raises:
            Exception: Fallback也失败
        """
        fallback_model = f"dashscope/{self.config.fallback_model}"
        
        logger.info(
            f"Calling fallback model: {fallback_model}",
            extra={
                "event": "llm.fallback.start",
                "agent": self.agent_name,
                "fallback_model": fallback_model
            }
        )
        
        try:
            response = litellm.completion(
                model=fallback_model,
                messages=messages,
                temperature=temperature if temperature is not None else self.config.temperature,
                max_tokens=max_tokens if max_tokens is not None else self.config.max_tokens,
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                **kwargs
            )
            
            logger.info(
                f"Fallback call success",
                extra={
                    "event": "llm.fallback.success",
                    "agent": self.agent_name,
                    "model": fallback_model,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                }
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(
                f"Fallback call failed: {type(e).__name__}: {str(e)[:200]}",
                extra={
                    "event": "llm.fallback.failed",
                    "agent": self.agent_name,
                    "model": fallback_model,
                    "error": str(e)[:200]
                }
            )
            raise


# ============================================
# 便捷工厂函数
# ============================================

def create_llm_client(agent_name: str) -> UnifiedLLMClient:
    """
    工厂函数：创建指定Agent的LLM客户端
    
    Args:
        agent_name: Agent名称
    
    Returns:
        UnifiedLLMClient实例
    
    Example:
        ```python
        client = create_llm_client("script_agent")
        response = client.chat([...])
        ```
    """
    return UnifiedLLMClient(agent_name=agent_name)


def test_connection(agent_name: str) -> bool:
    """
    测试指定Agent的LLM连接
    
    Args:
        agent_name: Agent名称
    
    Returns:
        连接是否成功
    """
    try:
        client = UnifiedLLMClient(agent_name=agent_name)
        response = client.chat([
            {'role': 'user', 'content': 'Hello, respond with "OK" only.'}
        ], max_tokens=10)
        
        logger.info(f"Connection test for {agent_name}: SUCCESS")
        return True
    
    except Exception as e:
        logger.error(f"Connection test for {agent_name}: FAILED - {e}")
        return False
