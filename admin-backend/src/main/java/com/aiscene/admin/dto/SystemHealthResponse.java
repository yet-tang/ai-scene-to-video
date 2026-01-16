package com.aiscene.admin.dto;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 系统健康状态响应 DTO
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Data
@Builder
public class SystemHealthResponse {

    private ServiceHealth backend;
    private ServiceHealth database;
    private ServiceHealth redis;
    private CeleryStatus celery;

    /**
     * 服务健康状态
     */
    @Data
    @Builder
    public static class ServiceHealth {
        private String name;
        private String status;
        private Integer responseTimeMs;
        private String message;
        private LocalDateTime checkedAt;

        public static final String STATUS_HEALTHY = "HEALTHY";
        public static final String STATUS_DEGRADED = "DEGRADED";
        public static final String STATUS_DOWN = "DOWN";
    }

    /**
     * Celery 状态
     */
    @Data
    @Builder
    public static class CeleryStatus {
        private String queueName;
        private Integer pendingTasks;
        private Integer activeTasks;
        private List<WorkerInfo> workers;
    }

    /**
     * Worker 信息
     */
    @Data
    @Builder
    public static class WorkerInfo {
        private String name;
        private String status;
        private Integer activeTasks;
        private Integer processedTasks;
    }
}
