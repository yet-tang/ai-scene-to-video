-- AI 模型配置表
-- 存储配置的 AI 大模型信息，用于监控和连通性测试

CREATE TABLE ai_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    api_key_env VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    last_test_at TIMESTAMP,
    last_test_status VARCHAR(20),
    last_test_latency_ms INTEGER,
    last_test_error TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ai_models_provider ON ai_models(provider);
CREATE INDEX idx_ai_models_agent_type ON ai_models(agent_type);
CREATE INDEX idx_ai_models_is_enabled ON ai_models(is_enabled);

-- 插入默认模型配置（基于 engine/llm_config.py）
INSERT INTO ai_models (provider, model_name, agent_type, api_key_env, description) VALUES
('dashscope', 'qwen3-vl-plus', 'vision_agent', 'DASHSCOPE_API_KEY', '视频理解 Agent，用于分析视频内容和场景识别'),
('xai', 'grok-4-1-fast-reasoning', 'selling_point_agent', 'GROK_API_KEY', '卖点提炼 Agent，用于生成营销文案'),
('volcengine', 'doubao-seed-1-8-251228', 'script_agent', 'VOLCENGINE_API_KEY', '脚本创作 Agent，用于生成视频解说脚本'),
('dashscope', 'qwen-plus', 'editing_agent', 'DASHSCOPE_API_KEY', '剪辑 Agent，用于视频编排决策'),
('dashscope', 'qwen-plus', 'audio_agent', 'DASHSCOPE_API_KEY', '音频 Agent，用于音频编排和 BGM 选择'),
('dashscope', 'qwen-plus', 'visual_agent', 'DASHSCOPE_API_KEY', '视觉 Agent，用于视觉增强决策'),
('dashscope', 'qwen3-max', 'orchestrator_agent', 'DASHSCOPE_API_KEY', '总导演 Agent，用于全局协调和质量把控');
