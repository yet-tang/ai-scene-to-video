package com.aiscene.admin.dto;

import com.aiscene.admin.entity.ProjectStatus;
import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.UUID;

/**
 * 项目列表项响应 DTO
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Data
@Builder
public class ProjectListItemResponse {

    private UUID id;
    private Long userId;
    private String title;
    private ProjectStatus status;
    private String errorStep;
    private LocalDateTime errorAt;
    private LocalDateTime createdAt;
    private int assetCount;
}
