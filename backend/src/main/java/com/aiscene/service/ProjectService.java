package com.aiscene.service;

import com.aiscene.dto.CreateProjectRequest;
import com.aiscene.entity.Asset;
import com.aiscene.entity.Project;
import com.aiscene.entity.ProjectStatus;
import com.aiscene.repository.AssetRepository;
import com.aiscene.repository.ProjectRepository;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.util.UUID;

@Service
@RequiredArgsConstructor
public class ProjectService {

    private final ProjectRepository projectRepository;
    private final AssetRepository assetRepository;
    private final StorageService storageService;
    private final ObjectMapper objectMapper;

    @Transactional
    public Project createProject(CreateProjectRequest request) {
        String houseInfoJson;
        try {
            houseInfoJson = objectMapper.writeValueAsString(request.getHouseInfo());
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Invalid house info format", e);
        }

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
        
        // Update status to UPLOADING if it's DRAFT
        if (project.getStatus() == ProjectStatus.DRAFT) {
            project.setStatus(ProjectStatus.UPLOADING);
            projectRepository.save(project);
        }

        String ossUrl = storageService.uploadFile(file);

        Asset asset = Asset.builder()
                .project(project)
                .ossUrl(ossUrl)
                // Duration will be extracted by Python worker later, or we can use ffprobe here if installed.
                // For MVP async flow, we leave it null or 0 for now.
                .duration(0.0) 
                .sortOrder(0) // Default order
                .build();

        return assetRepository.save(asset);
    }
}
