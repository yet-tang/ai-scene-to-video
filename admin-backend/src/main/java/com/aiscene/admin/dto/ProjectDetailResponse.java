package com.aiscene.admin.dto;

import com.aiscene.admin.entity.ProjectStatus;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

/**
 * 项目详情响应 DTO
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Data
@Builder
public class ProjectDetailResponse {

    private UUID id;
    private Long userId;
    private String title;
    private ProjectStatus status;
    private JsonNode houseInfo;
    private JsonNode scriptContent;
    private String audioUrl;
    private String bgmUrl;
    private String finalVideoUrl;

    // 错误信息
    private String errorLog;
    private String errorTaskId;
    private String errorRequestId;
    private String errorStep;
    private LocalDateTime errorAt;

    // 时间信息
    private LocalDateTime createdAt;

    // 关联数据
    private List<AssetSummary> assets;
    private ProcessingTimeline timeline;

    /**
     * 素材摘要
     */
    @Data
    @Builder
    public static class AssetSummary {
        private UUID id;
        private String ossUrl;
        private Double duration;
        private String sceneLabel;
        private Double sceneScore;
        private String userLabel;
        private Integer sortOrder;
    }

    /**
     * 处理时间线
     */
    @Data
    @Builder
    public static class ProcessingTimeline {
        private List<TimelineNode> nodes;
    }

    /**
     * 时间线节点
     */
    @Data
    @Builder
    public static class TimelineNode {
        private String step;
        private String status;
        private LocalDateTime startedAt;
        private LocalDateTime completedAt;
        private Integer durationMs;
        private String taskId;
        private String errorMessage;
    }
}
