package com.aiscene.admin.service;

import com.aiscene.admin.dto.DashboardStatsResponse;
import com.aiscene.admin.dto.ProjectDetailResponse;
import com.aiscene.admin.dto.ProjectListItemResponse;
import com.aiscene.admin.entity.Asset;
import com.aiscene.admin.entity.Project;
import com.aiscene.admin.entity.ProjectStatus;
import com.aiscene.admin.repository.AssetRepository;
import com.aiscene.admin.repository.ProjectRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * 项目监控服务
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ProjectMonitorService {

    private final ProjectRepository projectRepository;
    private final AssetRepository assetRepository;

    /**
     * 分页获取项目列表
     *
     * @param status   状态过滤（可选）
     * @param userId   用户ID过滤（可选）
     * @param pageable 分页参数
     * @return 项目分页
     */
    @Transactional(readOnly = true)
    public Page<ProjectListItemResponse> listProjects(ProjectStatus status, Long userId, Pageable pageable) {
        Page<Project> projects;

        if (status != null && userId != null) {
            projects = projectRepository.findByStatusAndUserId(status, userId, pageable);
        } else if (status != null) {
            projects = projectRepository.findByStatus(status, pageable);
        } else if (userId != null) {
            projects = projectRepository.findByUserId(userId, pageable);
        } else {
            projects = projectRepository.findAll(pageable);
        }

        return projects.map(this::toListItem);
    }

    /**
     * 获取项目详情
     *
     * @param projectId 项目ID
     * @return 项目详情
     */
    @Transactional(readOnly = true)
    public ProjectDetailResponse getProjectDetail(UUID projectId) {
        Project project = projectRepository.findById(projectId)
                .orElseThrow(() -> new IllegalArgumentException("项目不存在"));

        List<Asset> assets = assetRepository.findByProjectIdOrderBySortOrder(projectId);
        List<ProjectDetailResponse.AssetSummary> assetSummaries = assets.stream()
                .map(this::toAssetSummary)
                .toList();

        ProjectDetailResponse.ProcessingTimeline timeline = buildTimeline(project);

        return ProjectDetailResponse.builder()
                .id(project.getId())
                .userId(project.getUserId())
                .title(project.getTitle())
                .status(project.getStatus())
                .houseInfo(project.getHouseInfo())
                .scriptContent(project.getScriptContent())
                .audioUrl(project.getAudioUrl())
                .bgmUrl(project.getBgmUrl())
                .finalVideoUrl(project.getFinalVideoUrl())
                .errorLog(project.getErrorLog())
                .errorTaskId(project.getErrorTaskId())
                .errorRequestId(project.getErrorRequestId())
                .errorStep(project.getErrorStep())
                .errorAt(project.getErrorAt())
                .createdAt(project.getCreatedAt())
                .assets(assetSummaries)
                .timeline(timeline)
                .build();
    }

    /**
     * 获取仪表盘统计数据
     *
     * @return 统计数据
     */
    @Transactional(readOnly = true)
    public DashboardStatsResponse getDashboardStats() {
        LocalDateTime startOfDay = LocalDate.now().atStartOfDay();

        long totalProjects = projectRepository.count();
        long todayCreated = projectRepository.countTodayCreated(startOfDay);
        long todayCompleted = projectRepository.countTodayCompleted(startOfDay);
        long todayFailed = projectRepository.countTodayFailed(startOfDay);

        // 统计处理中的项目
        long processingProjects = projectRepository.countByStatus(ProjectStatus.ANALYZING)
                + projectRepository.countByStatus(ProjectStatus.SCRIPT_GENERATING)
                + projectRepository.countByStatus(ProjectStatus.AUDIO_GENERATING)
                + projectRepository.countByStatus(ProjectStatus.RENDERING);

        return DashboardStatsResponse.builder()
                .totalProjects(totalProjects)
                .todayCreated(todayCreated)
                .todayCompleted(todayCompleted)
                .todayFailed(todayFailed)
                .processingProjects(processingProjects)
                .build();
    }

    /**
     * 转换为列表项
     */
    private ProjectListItemResponse toListItem(Project project) {
        long assetCount = assetRepository.countByProjectId(project.getId());
        return ProjectListItemResponse.builder()
                .id(project.getId())
                .userId(project.getUserId())
                .title(project.getTitle())
                .status(project.getStatus())
                .errorStep(project.getErrorStep())
                .errorAt(project.getErrorAt())
                .createdAt(project.getCreatedAt())
                .assetCount((int) assetCount)
                .build();
    }

    /**
     * 转换为素材摘要
     */
    private ProjectDetailResponse.AssetSummary toAssetSummary(Asset asset) {
        return ProjectDetailResponse.AssetSummary.builder()
                .id(asset.getId())
                .ossUrl(asset.getOssUrl())
                .duration(asset.getDuration())
                .sceneLabel(asset.getSceneLabel())
                .sceneScore(asset.getSceneScore())
                .userLabel(asset.getUserLabel())
                .sortOrder(asset.getSortOrder())
                .build();
    }

    /**
     * 构建处理时间线
     */
    private ProjectDetailResponse.ProcessingTimeline buildTimeline(Project project) {
        List<ProjectDetailResponse.TimelineNode> nodes = new ArrayList<>();
        ProjectStatus currentStatus = project.getStatus();

        // 定义处理步骤顺序
        List<String> steps = List.of(
                "UPLOADING", "ANALYZING", "REVIEW", "SCRIPT_GENERATING",
                "AUDIO_GENERATING", "RENDERING", "COMPLETED"
        );

        for (String step : steps) {
            ProjectStatus stepStatus = ProjectStatus.valueOf(step);
            String nodeStatus;

            if (currentStatus == ProjectStatus.FAILED && step.equals(project.getErrorStep())) {
                nodeStatus = "FAILED";
            } else if (stepStatus.ordinal() < currentStatus.ordinal()) {
                nodeStatus = "SUCCESS";
            } else if (stepStatus.ordinal() == currentStatus.ordinal()) {
                nodeStatus = currentStatus == ProjectStatus.COMPLETED ? "SUCCESS" : "RUNNING";
            } else {
                nodeStatus = "PENDING";
            }

            ProjectDetailResponse.TimelineNode node = ProjectDetailResponse.TimelineNode.builder()
                    .step(step)
                    .status(nodeStatus)
                    .build();

            // 如果是失败节点，添加错误信息
            if (nodeStatus.equals("FAILED")) {
                node.setTaskId(project.getErrorTaskId());
                node.setErrorMessage(project.getErrorLog() != null ?
                        project.getErrorLog().substring(0, Math.min(500, project.getErrorLog().length())) : null);
            }

            nodes.add(node);
        }

        return ProjectDetailResponse.ProcessingTimeline.builder()
                .nodes(nodes)
                .build();
    }
}
