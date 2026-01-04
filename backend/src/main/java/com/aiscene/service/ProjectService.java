package com.aiscene.service;

import com.aiscene.dto.AssetConfirmRequest;
import com.aiscene.dto.CreateProjectRequest;
import com.aiscene.dto.UpdateAssetRequest;
import com.aiscene.entity.Asset;
import com.aiscene.entity.Project;
import com.aiscene.entity.ProjectStatus;
import com.aiscene.repository.AssetRepository;
import com.aiscene.repository.ProjectRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
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

        // Construct public URL
        String ossUrl = storageService.getPublicUrl(request.getObjectKey());

        int nextSortOrder = assetRepository.findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(projectId).size();
        Asset asset = Asset.builder()
                .project(project)
                .ossUrl(ossUrl)
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
                .assets(assets)
                .scriptContent(project.getScriptContent()) // Might be null initially
                .build();
    }

    @Transactional
    public Asset updateAsset(UUID assetId, UpdateAssetRequest request) {
        Asset asset = assetRepository.findById(assetId)
                .orElseThrow(() -> new RuntimeException("Asset not found"));

        if (request.getUserLabel() != null) {
            asset.setUserLabel(request.getUserLabel());
            // Also update sceneLabel if user explicitly changes it (frontend usually sends userLabel)
            // Or we keep sceneLabel as AI result and use userLabel for display/generation priority.
            // Logic: script generation uses scene_label in current code. 
            // We should probably update sceneLabel too OR make script gen prefer userLabel.
            // Let's look at `generateScript`... it puts `scene_label` into the map.
            // To be safe for now, let's update sceneLabel too if userLabel is provided, 
            // so existing script gen logic picks it up.
            // Ideally we should refactor script gen to look at userLabel first.
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
            map.put("asset_id", asset.getId().toString());
            map.put("scene_label", asset.getSceneLabel());
            map.put("scene_score", asset.getSceneScore());
            map.put("oss_url", asset.getOssUrl());
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
        project.setScriptContent(scriptContent);
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
        project.setScriptContent(scriptContent);
        project.setStatus(ProjectStatus.SCRIPT_GENERATED);
        projectRepository.save(project);
    }

    @Transactional
    public void renderVideo(UUID projectId) {
        Project project = getProject(projectId);
        String scriptContent = project.getScriptContent();
        if (scriptContent == null || scriptContent.trim().isEmpty()) {
            throw new IllegalStateException("Script content is empty");
        }

        List<Asset> assets = assetRepository.findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(projectId);
        if (assets.isEmpty()) {
            throw new IllegalStateException("No assets to render");
        }
        
        // Prepare data for rendering
        List<Object> timelineAssets = assets.stream().map(asset -> {
            Map<String, Object> map = new HashMap<>();
            map.put("oss_url", asset.getOssUrl());
            map.put("duration", asset.getDuration());
            return map;
        }).collect(Collectors.toList());

        project.setStatus(ProjectStatus.AUDIO_GENERATING);
        projectRepository.save(project);
        
        taskQueueService.submitRenderPipelineTask(projectId, scriptContent, timelineAssets);
    }

    @Transactional
    public Project createProject(CreateProjectRequest request) {
        JsonNode houseInfoJson = objectMapper.valueToTree(request.getHouseInfo());

        Project project = Project.builder()
                .userId(request.getUserId())
                .title(request.getTitle())
                .houseInfo(houseInfoJson)
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

        // Save file locally for local split optimization
        String ossUrl;
        try {
            // Ensure temp directory exists
            java.nio.file.Path tempDir = java.nio.file.Paths.get("/tmp/ai-video-uploads");
            if (!java.nio.file.Files.exists(tempDir)) {
                java.nio.file.Files.createDirectories(tempDir);
            }
            
            // Save file to local temp
            String originalFilename = file.getOriginalFilename();
            String extension = "";
            if (originalFilename != null && originalFilename.contains(".")) {
                extension = originalFilename.substring(originalFilename.lastIndexOf("."));
            }
            String localFilename = UUID.randomUUID() + extension;
            java.nio.file.Path localPath = tempDir.resolve(localFilename);
            file.transferTo(localPath.toFile());
            
            // Use file:// protocol for Worker to recognize local path
            ossUrl = "file://" + localPath.toAbsolutePath().toString();
            
        } catch (java.io.IOException e) {
            // Fallback to S3 upload if local save fails
            ossUrl = storageService.uploadFile(file);
        }

        Asset asset = Asset.builder()
                .project(project)
                .ossUrl(ossUrl)
                // Duration will be extracted by Python worker later, or we can use ffprobe here if installed.
                // For MVP async flow, we leave it null or 0 for now.
                .duration(0.0) 
                .sortOrder(0) // Default order
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

        String ossUrl;
        try {
            java.nio.file.Path tempDir = java.nio.file.Paths.get("/tmp/ai-video-uploads");
            if (!java.nio.file.Files.exists(tempDir)) {
                java.nio.file.Files.createDirectories(tempDir);
            }

            String originalFilename = file.getOriginalFilename();
            String extension = "";
            if (originalFilename != null && originalFilename.contains(".")) {
                extension = originalFilename.substring(originalFilename.lastIndexOf("."));
            }
            String localFilename = UUID.randomUUID() + extension;
            java.nio.file.Path localPath = tempDir.resolve(localFilename);
            file.transferTo(localPath.toFile());

            String base = localAssetBaseUrl == null ? "" : localAssetBaseUrl.trim();
            if (base.endsWith("/")) {
                base = base.substring(0, base.length() - 1);
            }
            ossUrl = base + "/" + localFilename;

        } catch (java.io.IOException e) {
            throw new RuntimeException("Failed to save file locally", e);
        }

        int nextSortOrder = assetRepository.findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(projectId).size();
        Asset asset = Asset.builder()
                .project(project)
                .ossUrl(ossUrl)
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
}
