package com.aiscene.admin.dto;

import lombok.Builder;
import lombok.Data;

/**
 * 仪表盘统计响应 DTO
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Data
@Builder
public class DashboardStatsResponse {

    // 项目统计
    private long totalProjects;
    private long todayCreated;
    private long todayCompleted;
    private long todayFailed;
    private long processingProjects;

    // 模型统计
    private int totalModels;
    private int healthyModels;
    private int unhealthyModels;
}
