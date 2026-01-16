package com.aiscene.admin.dto;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.UUID;

/**
 * 模型状态响应 DTO
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Data
@Builder
public class ModelStatusResponse {

    private UUID id;
    private String provider;
    private String modelName;
    private String agentType;
    private String description;
    private Boolean isEnabled;
    private Boolean apiKeyConfigured;

    // 最近测试结果
    private LocalDateTime lastTestAt;
    private String lastTestStatus;
    private Integer lastTestLatencyMs;
    private String lastTestError;
}
