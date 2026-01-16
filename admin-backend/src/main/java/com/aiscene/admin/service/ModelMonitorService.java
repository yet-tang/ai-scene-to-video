package com.aiscene.admin.service;

import com.aiscene.admin.dto.ModelStatusResponse;
import com.aiscene.admin.entity.AiModel;
import com.aiscene.admin.repository.AiModelRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * 模型监控服务
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ModelMonitorService {

    private final AiModelRepository aiModelRepository;
    private final RestTemplate restTemplate = new RestTemplate();

    /**
     * 获取所有模型状态
     *
     * @return 模型状态列表
     */
    @Transactional(readOnly = true)
    public List<ModelStatusResponse> listModels() {
        return aiModelRepository.findAll().stream()
                .map(this::toModelStatus)
                .toList();
    }

    /**
     * 获取单个模型状态
     *
     * @param modelId 模型ID
     * @return 模型状态
     */
    @Transactional(readOnly = true)
    public ModelStatusResponse getModel(UUID modelId) {
        AiModel model = aiModelRepository.findById(modelId)
                .orElseThrow(() -> new IllegalArgumentException("模型不存在"));
        return toModelStatus(model);
    }

    /**
     * 测试模型连通性
     *
     * @param modelId 模型ID
     * @return 测试结果
     */
    @Transactional
    public ModelStatusResponse testModel(UUID modelId) {
        AiModel model = aiModelRepository.findById(modelId)
                .orElseThrow(() -> new IllegalArgumentException("模型不存在"));

        String apiKey = System.getenv(model.getApiKeyEnv());
        if (apiKey == null || apiKey.isBlank()) {
            model.setLastTestAt(LocalDateTime.now());
            model.setLastTestStatus(AiModel.TEST_STATUS_FAILED);
            model.setLastTestError("API Key 未配置: " + model.getApiKeyEnv());
            model.setLastTestLatencyMs(0);
            aiModelRepository.save(model);
            return toModelStatus(model);
        }

        long startTime = System.currentTimeMillis();
        try {
            testModelConnection(model.getProvider(), model.getModelName(), apiKey);
            int latencyMs = (int) (System.currentTimeMillis() - startTime);

            model.setLastTestAt(LocalDateTime.now());
            model.setLastTestStatus(AiModel.TEST_STATUS_SUCCESS);
            model.setLastTestLatencyMs(latencyMs);
            model.setLastTestError(null);

            log.info("Model test success: {} - {}ms", model.getModelName(), latencyMs);
        } catch (Exception e) {
            int latencyMs = (int) (System.currentTimeMillis() - startTime);

            model.setLastTestAt(LocalDateTime.now());
            model.setLastTestStatus(AiModel.TEST_STATUS_FAILED);
            model.setLastTestLatencyMs(latencyMs);
            model.setLastTestError(e.getMessage());

            log.error("Model test failed: {} - {}", model.getModelName(), e.getMessage());
        }

        aiModelRepository.save(model);
        return toModelStatus(model);
    }

    /**
     * 执行实际的模型连接测试
     */
    private void testModelConnection(String provider, String modelName, String apiKey) {
        String endpoint = getProviderEndpoint(provider);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        // 设置认证头
        if ("dashscope".equals(provider)) {
            headers.set("Authorization", "Bearer " + apiKey);
        } else if ("openai".equals(provider) || "xai".equals(provider)) {
            headers.set("Authorization", "Bearer " + apiKey);
        } else if ("volcengine".equals(provider)) {
            headers.set("Authorization", "Bearer " + apiKey);
        }

        Map<String, Object> body = Map.of(
                "model", modelName,
                "messages", List.of(
                        Map.of("role", "user", "content", "Hello")
                ),
                "max_tokens", 5
        );

        HttpEntity<Map<String, Object>> request = new HttpEntity<>(body, headers);
        restTemplate.postForEntity(endpoint, request, String.class);
    }

    /**
     * 获取提供商的 API 端点
     */
    private String getProviderEndpoint(String provider) {
        return switch (provider) {
            case "dashscope" -> "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions";
            case "openai" -> "https://api.openai.com/v1/chat/completions";
            case "xai" -> "https://api.x.ai/v1/chat/completions";
            case "volcengine" -> "https://ark.cn-beijing.volces.com/api/v3/chat/completions";
            default -> throw new IllegalArgumentException("未知的提供商: " + provider);
        };
    }

    /**
     * 转换为模型状态响应
     */
    private ModelStatusResponse toModelStatus(AiModel model) {
        return ModelStatusResponse.builder()
                .id(model.getId())
                .provider(model.getProvider())
                .modelName(model.getModelName())
                .agentType(model.getAgentType())
                .description(model.getDescription())
                .isEnabled(model.getIsEnabled())
                .apiKeyConfigured(model.isApiKeyConfigured())
                .lastTestAt(model.getLastTestAt())
                .lastTestStatus(model.getLastTestStatus())
                .lastTestLatencyMs(model.getLastTestLatencyMs())
                .lastTestError(model.getLastTestError())
                .build();
    }

    /**
     * 获取健康模型数量
     */
    public int countHealthyModels() {
        return (int) aiModelRepository.findByIsEnabledTrue().stream()
                .filter(m -> AiModel.TEST_STATUS_SUCCESS.equals(m.getLastTestStatus()))
                .count();
    }

    /**
     * 获取不健康模型数量
     */
    public int countUnhealthyModels() {
        return (int) aiModelRepository.findByIsEnabledTrue().stream()
                .filter(m -> !AiModel.TEST_STATUS_SUCCESS.equals(m.getLastTestStatus()))
                .count();
    }
}
