package com.aiscene.admin.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;
import java.util.UUID;

/**
 * AI 模型配置实体
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Data
@Entity
@Table(name = "ai_models")
public class AiModel {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false, length = 50)
    private String provider;

    @Column(name = "model_name", nullable = false, length = 100)
    private String modelName;

    @Column(name = "agent_type", nullable = false, length = 50)
    private String agentType;

    @Column(name = "api_key_env", nullable = false, length = 100)
    private String apiKeyEnv;

    @Column(length = 255)
    private String description;

    @Column(name = "is_enabled", nullable = false)
    private Boolean isEnabled = true;

    @Column(name = "last_test_at")
    private LocalDateTime lastTestAt;

    @Column(name = "last_test_status", length = 20)
    private String lastTestStatus;

    @Column(name = "last_test_latency_ms")
    private Integer lastTestLatencyMs;

    @Column(name = "last_test_error", columnDefinition = "text")
    private String lastTestError;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    /**
     * 测试状态常量
     */
    public static final String TEST_STATUS_SUCCESS = "SUCCESS";
    public static final String TEST_STATUS_FAILED = "FAILED";

    /**
     * 检查 API Key 是否已配置
     *
     * @return true 如果环境变量已设置
     */
    public boolean isApiKeyConfigured() {
        String apiKey = System.getenv(apiKeyEnv);
        return apiKey != null && !apiKey.isBlank();
    }
}
