package com.aiscene.admin.controller;

import com.aiscene.admin.dto.DashboardStatsResponse;
import com.aiscene.admin.dto.ProjectDetailResponse;
import com.aiscene.admin.dto.ProjectListItemResponse;
import com.aiscene.admin.entity.ProjectStatus;
import com.aiscene.admin.service.ModelMonitorService;
import com.aiscene.admin.service.ProjectMonitorService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

/**
 * 项目监控控制器
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Slf4j
@RestController
@RequestMapping("/admin/projects")
@RequiredArgsConstructor
public class ProjectMonitorController {

    private final ProjectMonitorService projectMonitorService;
    private final ModelMonitorService modelMonitorService;

    /**
     * 获取仪表盘统计数据
     *
     * @return 统计数据
     */
    @GetMapping("/stats")
    public ResponseEntity<DashboardStatsResponse> getDashboardStats() {
        DashboardStatsResponse stats = projectMonitorService.getDashboardStats();

        // 补充模型统计
        int totalModels = modelMonitorService.listModels().size();
        int healthyModels = modelMonitorService.countHealthyModels();
        int unhealthyModels = modelMonitorService.countUnhealthyModels();

        stats.setTotalModels(totalModels);
        stats.setHealthyModels(healthyModels);
        stats.setUnhealthyModels(unhealthyModels);

        return ResponseEntity.ok(stats);
    }

    /**
     * 分页获取项目列表
     *
     * @param page   页码（从0开始）
     * @param size   每页大小
     * @param status 状态过滤
     * @param userId 用户ID过滤
     * @return 项目分页
     */
    @GetMapping
    public ResponseEntity<Page<ProjectListItemResponse>> listProjects(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) ProjectStatus status,
            @RequestParam(required = false) Long userId) {

        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<ProjectListItemResponse> projects = projectMonitorService.listProjects(status, userId, pageable);
        return ResponseEntity.ok(projects);
    }

    /**
     * 获取项目详情
     *
     * @param id 项目ID
     * @return 项目详情
     */
    @GetMapping("/{id}")
    public ResponseEntity<ProjectDetailResponse> getProjectDetail(@PathVariable UUID id) {
        ProjectDetailResponse detail = projectMonitorService.getProjectDetail(id);
        return ResponseEntity.ok(detail);
    }
}
