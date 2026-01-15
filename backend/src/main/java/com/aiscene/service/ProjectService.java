package com.aiscene.service;

import com.aiscene.dto.AssetConfirmRequest;
import com.aiscene.dto.CreateProjectRequest;
import com.aiscene.dto.UpdateAssetRequest;
import com.aiscene.entity.Asset;
import com.aiscene.entity.Project;
import com.aiscene.entity.ProjectStatus;
import com.aiscene.config.BgmConfig;
import com.aiscene.repository.AssetRepository;
import com.aiscene.repository.ProjectRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.util.UUID;

import com.aiscene.dto.TimelineResponse;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.HashMap;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class ProjectService {

    private final ProjectRepository projectRepository;
    private final AssetRepository assetRepository;
    private final StorageService storageService;
    private final TaskQueueService taskQueueService;
    private final ObjectMapper objectMapper;
    private final JdbcTemplate jdbcTemplate;
    private final BgmConfig bgmConfig;

    @Value("${app.local-asset-base-url:http://ai-scene-backend:8090/public}")
    private String localAssetBaseUrl;

    // ... existing methods ...

    @Transactional
    public Asset confirmAsset(UUID projectId, AssetConfirmRequest request) {
        Project project = getProject(projectId);

        if (project.getStatus() == ProjectStatus.DRAFT) {
            project.setStatus(ProjectStatus.UPLOADING);
            projectRepository.save(project);
        }

        String objectKey = request.getObjectKey();
        String ossUrl = storageService.getPublicUrl(objectKey);

        int nextSortOrder = assetRepository.findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(projectId).size();
        Asset asset = Asset.builder()
                .project(project)
                .ossUrl(ossUrl)
                .storageType("S3")
                .storageBucket(storageService.getBucketName())
                .storageKey(objectKey)
                // Duration will be extracted by Python worker later
                .duration(0.0)
                .sortOrder(nextSortOrder)
                .build();

        Asset savedAsset = assetRepository.save(asset);

        // Submit Analysis Task
        taskQueueService.submitAnalysisTask(project.getId(), savedAsset.getId(), savedAsset.getOssUrl());

        if (project.getStatus() == ProjectStatus.DRAFT || project.getStatus() == ProjectStatus.UPLOADING) {
            project.setStatus(ProjectStatus.ANALYZING);
            projectRepository.save(project);
        }

        return savedAsset;
    }

    public TimelineResponse getSmartTimeline(UUID projectId) {
        Project project = getProject(projectId);
        List<Asset> assets = assetRepository.findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(projectId);

        // Simple Smart Sort Logic
        // Define priority: Gate > Living > Dining > Kitchen > Bedroom > Toilet > Balcony > Others
        Map<String, Integer> scenePriority = new HashMap<>();
        scenePriority.put("小区门头", 10);
        scenePriority.put("小区环境", 20);
        scenePriority.put("客厅", 30);
        scenePriority.put("餐厅", 40);
        scenePriority.put("厨房", 50);
        scenePriority.put("卧室", 60);
        scenePriority.put("卫生间", 70);
        scenePriority.put("阳台", 80);
        scenePriority.put("走廊", 90);
        
        // Check if assets have been analyzed (have scene labels)
        boolean hasAnalysis = assets.stream().anyMatch(a -> a.getSceneLabel() != null);

        if (hasAnalysis) {
            // Sort based on priority map
            assets.sort(Comparator.comparingInt(a -> {
                String label = a.getSceneLabel();
                if (label == null) return 999;
                return scenePriority.getOrDefault(label, 100);
            }));
        }

        return TimelineResponse.builder()
                .projectId(project.getId().toString())
                .projectTitle(project.getTitle())
                .status(project.getStatus())
                .errorRequestId(project.getErrorRequestId())
                .errorStep(project.getErrorStep())
                .assets(assets)
                .scriptContent(project.getScriptContent())
                .build();
    }

    @Transactional
    public Asset updateAsset(UUID assetId, UpdateAssetRequest request) {
        Asset asset = assetRepository.findById(assetId)
                .orElseThrow(() -> new RuntimeException("Asset not found"));

        if (request.getUserLabel() != null) {
            asset.setUserLabel(request.getUserLabel());
            asset.setSceneLabel(request.getUserLabel());
        }
        
        if (request.getSortOrder() != null) {
            asset.setSortOrder(request.getSortOrder());
        }

        return assetRepository.save(asset);
    }

    @Transactional
    public String generateScript(UUID projectId) {
        Project project = getProject(projectId);
        List<Asset> assets = assetRepository.findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(projectId);

        Object houseInfo = objectMapper.convertValue(project.getHouseInfo(), Object.class);

        // Convert assets to simple list of maps/objects for Python
        List<Object> timelineData = assets.stream().map(asset -> {
            Map<String, Object> map = new HashMap<>();
            map.put("id", asset.getId().toString());
            map.put("scene_label", asset.getSceneLabel());
            map.put("scene_score", asset.getSceneScore());
            map.put("oss_url", asset.getOssUrl());
            map.put("duration", asset.getDuration());
            return map;
        }).collect(Collectors.toList());

        project.setStatus(ProjectStatus.SCRIPT_GENERATING);
        projectRepository.save(project);

        return taskQueueService.submitScriptGenerationTask(projectId, houseInfo, timelineData);
    }
    
    @Transactional
    public void generateAudio(UUID projectId, String scriptContent) {
        // Optional: Update script content in DB if user edited it
        Project project = getProject(projectId);
        try {
            JsonNode scriptNode = scriptContent != null ? objectMapper.readTree(scriptContent) : null;
            project.setScriptContent(scriptNode);
        } catch (Exception e) {
            throw new RuntimeException("Invalid script content format", e);
        }
        project.setStatus(ProjectStatus.AUDIO_GENERATING);
        projectRepository.save(project);
        
        taskQueueService.submitAudioGenerationTask(projectId, scriptContent);
    }

    @Transactional
    public void updateScriptContent(UUID projectId, String scriptContent) {
        Project project = getProject(projectId);
        if (project.getStatus() == ProjectStatus.COMPLETED) {
            throw new IllegalStateException("Project already completed");
        }
        if (
                project.getStatus() == ProjectStatus.AUDIO_GENERATING
                        || project.getStatus() == ProjectStatus.AUDIO_GENERATED
                        || project.getStatus() == ProjectStatus.RENDERING
        ) {
            throw new IllegalStateException("Project is processing");
        }
        try {
            JsonNode scriptNode = scriptContent != null ? objectMapper.readTree(scriptContent) : null;
            project.setScriptContent(scriptNode);
        } catch (Exception e) {
            throw new RuntimeException("Invalid script content format", e);
        }
        project.setStatus(ProjectStatus.SCRIPT_GENERATED);
        projectRepository.save(project);
    }

    @Transactional
    public void renderVideo(UUID projectId) {
        Project project = getProject(projectId);
        JsonNode scriptNode = project.getScriptContent();
        if (scriptNode == null || scriptNode.isNull() || scriptNode.isEmpty()) {
            throw new IllegalStateException("Script content is empty");
        }
        
        String scriptContent = scriptNode.isTextual() ? scriptNode.asText() : scriptNode.toString();

        List<Asset> assets = assetRepository.findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(projectId);
        if (assets.isEmpty()) {
            throw new IllegalStateException("No assets to render");
        }
        
        // Prepare data for rendering
        List<Object> timelineAssets = assets.stream().map(asset -> {
            Map<String, Object> map = new HashMap<>();
            map.put("id", asset.getId().toString());
            map.put("oss_url", asset.getOssUrl());
            map.put("duration", asset.getDuration());
            return map;
        }).collect(Collectors.toList());

        int updated = projectRepository.updateStatusIfIn(
                projectId,
                List.of(ProjectStatus.SCRIPT_GENERATED, ProjectStatus.FAILED),
                ProjectStatus.RENDERING);
        if (updated == 0) {
            if (project.getStatus() == ProjectStatus.RENDERING || project.getStatus() == ProjectStatus.AUDIO_GENERATING) {
                throw new IllegalStateException("Project is processing");
            }
            throw new IllegalStateException("Project is not ready to render");
        }
        
        // Pass BGM URL to rendering task
        String bgmUrl = project.getBgmUrl();
        taskQueueService.submitRenderPipelineTask(projectId, scriptContent, timelineAssets, bgmUrl);
    }

    @Transactional
    public Project createProject(CreateProjectRequest request) {
        JsonNode houseInfoJson = objectMapper.valueToTree(request.getHouseInfo());

        // Auto-select a random BGM from built-in list
        String bgmUrl = null;
        if (bgmConfig.isAutoSelect() && bgmConfig.hasBuiltinBgm()) {
            bgmUrl = bgmConfig.getRandomBgmUrl();
        }

        Project project = Project.builder()
                .userId(request.getUserId())
                .title(request.getTitle())
                .houseInfo(houseInfoJson)
                .bgmUrl(bgmUrl)
                .status(ProjectStatus.DRAFT)
                .build();

        return projectRepository.save(project);
    }

    public Project getProject(UUID id) {
        return projectRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Project not found"));
    }

    @Transactional
    public Asset uploadAsset(UUID projectId, MultipartFile file) {
        Project project = getProject(projectId);
        
        if (project.getStatus() == ProjectStatus.DRAFT) {
            project.setStatus(ProjectStatus.UPLOADING);
            projectRepository.save(project);
        }

        StorageService.UploadedObject uploaded = storageService.uploadFileAndReturnObject(file);

        int nextSortOrder = assetRepository.findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(projectId).size();
        Asset asset = Asset.builder()
                .project(project)
                .ossUrl(uploaded.publicUrl())
                .storageType("S3")
                .storageBucket(storageService.getBucketName())
                .storageKey(uploaded.objectKey())
                .duration(0.0)
                .sortOrder(nextSortOrder)
                .build();

        Asset savedAsset = assetRepository.save(asset);

        // Submit Analysis Task to Redis Queue
        taskQueueService.submitAnalysisTask(project.getId(), savedAsset.getId(), savedAsset.getOssUrl());

        if (project.getStatus() == ProjectStatus.DRAFT || project.getStatus() == ProjectStatus.UPLOADING) {
            project.setStatus(ProjectStatus.ANALYZING);
            projectRepository.save(project);
        }

        return savedAsset;
    }

    @Transactional
    public Asset uploadAssetLocal(UUID projectId, MultipartFile file) {
        Project project = getProject(projectId);

        if (project.getStatus() == ProjectStatus.DRAFT) {
            project.setStatus(ProjectStatus.UPLOADING);
            projectRepository.save(project);
        }

        StorageService.UploadedObject uploaded = storageService.uploadFileAndReturnObject(file);

        int nextSortOrder = assetRepository.findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(projectId).size();
        Asset asset = Asset.builder()
                .project(project)
                .ossUrl(uploaded.publicUrl())
                .storageType("S3")
                .storageBucket(storageService.getBucketName())
                .storageKey(uploaded.objectKey())
                .duration(0.0)
                .sortOrder(nextSortOrder)
                .build();

        Asset savedAsset = assetRepository.save(asset);

        taskQueueService.submitAnalysisTask(project.getId(), savedAsset.getId(), savedAsset.getOssUrl());

        if (project.getStatus() == ProjectStatus.DRAFT || project.getStatus() == ProjectStatus.UPLOADING) {
            project.setStatus(ProjectStatus.ANALYZING);
            projectRepository.save(project);
        }

        return savedAsset;
    }

    public Page<Project> listProjects(Long userId, int page, int size) {
        Pageable pageable = PageRequest.of(page - 1, size, Sort.by("createdAt").descending());
        if (userId == null) {
            return projectRepository.findAll(pageable);
        }
        return projectRepository.findAllByUserId(userId, pageable);
    }

    @Transactional
    public void updateScriptContent(UUID projectId, String scriptContent, Long userId) {
        Project project = getProject(projectId);
        validateProjectOwnership(project, userId);
        updateScriptContent(projectId, scriptContent);
    }

    @Transactional
    public void retryRender(UUID projectId, Long userId) {
        Project project = getProject(projectId);
        validateProjectOwnership(project, userId);
        renderVideo(projectId);
    }

    @Transactional
    public void resetAllData() {
        jdbcTemplate.execute("TRUNCATE TABLE render_jobs, assets, projects RESTART IDENTITY CASCADE");
    }

    private void validateProjectOwnership(Project project, Long userId) {
        if (userId == null) {
            return;
        }
        if (project.getUserId() == null || !userId.equals(project.getUserId())) {
            throw new IllegalStateException("Forbidden");
        }
    }
}
