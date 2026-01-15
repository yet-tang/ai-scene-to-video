package com.aiscene.controller;

import com.aiscene.dto.AssetConfirmRequest;
import com.aiscene.dto.CreateProjectRequest;
import com.aiscene.dto.PresignedUrlResponse;
import com.aiscene.dto.ProjectListItemResponse;
import com.aiscene.dto.TimelineResponse;
import com.aiscene.dto.UpdateAssetRequest;
import com.aiscene.entity.Asset;
import com.aiscene.entity.Project;
import com.aiscene.entity.ProjectStatus;
import com.aiscene.service.ProjectService;
import com.aiscene.service.StorageService;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.data.domain.Page;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.UUID;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/v1/projects")
@RequiredArgsConstructor
public class ProjectController {

    private final ProjectService projectService;
    private final StorageService storageService;

    @Value("${app.dev-reset-enabled:false}")
    private boolean devResetEnabled;

    @Value("${app.upload.allowed-content-types:video/mp4,video/quicktime,video/x-m4v,video/webm,video/3gpp,video/3gpp2}")
    private List<String> allowedContentTypes;

    @GetMapping
    public ResponseEntity<Page<ProjectListItemResponse>> listProjects(
            @RequestHeader(value = "X-User-Id", required = false) Long userId,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        Page<Project> projectPage = projectService.listProjects(userId, page, size);
        Page<ProjectListItemResponse> body = projectPage.map(p -> ProjectListItemResponse.builder()
                .id(p.getId())
                .title(p.getTitle())
                .status(p.getStatus())
                .houseInfo(p.getHouseInfo())
                .createdAt(p.getCreatedAt())
                .errorRequestId(p.getErrorRequestId())
                .errorStep(p.getErrorStep())
                .errorAt(p.getErrorAt())
                .build());
        return ResponseEntity.ok(body);
    }

    @PostMapping
    public ResponseEntity<Project> createProject(@RequestBody CreateProjectRequest request) {
        Project project = projectService.createProject(request);
        return ResponseEntity.ok(project);
    }

    @GetMapping("/{id}")
    public ResponseEntity<Project> getProject(@PathVariable UUID id) {
        Project project = projectService.getProject(id);
        return ResponseEntity.ok(project);
    }

    @PostMapping("/{id}/assets/presign")
    public ResponseEntity<PresignedUrlResponse> getPresignedUrl(
            @PathVariable UUID id,
            @RequestParam String filename,
            @RequestParam String contentType) {
        validateContentType(contentType);
        String objectKey = UUID.randomUUID() + "-" + filename;
        PresignedUrlResponse response = storageService.generatePresignedUrl(objectKey, contentType);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/{id}/assets/confirm")
    public ResponseEntity<Asset> confirmAsset(@PathVariable UUID id, @RequestBody AssetConfirmRequest request) {
        validateContentType(request == null ? null : request.getContentType());
        Asset asset = projectService.confirmAsset(id, request);
        return ResponseEntity.ok(asset);
    }

    @PostMapping("/{id}/assets")
    public ResponseEntity<Asset> uploadAsset(@PathVariable UUID id, @RequestParam("file") MultipartFile file) {
        validateContentType(file == null ? null : file.getContentType());
        Asset asset = projectService.uploadAsset(id, file);
        return ResponseEntity.ok(asset);
    }

    @PostMapping("/{id}/assets/local")
    public ResponseEntity<Asset> uploadAssetLocal(@PathVariable UUID id, @RequestParam("file") MultipartFile file) {
        validateContentType(file == null ? null : file.getContentType());
        Asset asset = projectService.uploadAssetLocal(id, file);
        return ResponseEntity.ok(asset);
    }

    private void validateContentType(String contentType) {
        String normalized = normalizeContentType(contentType);
        if (normalized == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Missing Content-Type");
        }
        if (allowedContentTypes == null || allowedContentTypes.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Upload content-type whitelist is not configured");
        }
        if (!allowedContentTypes.contains(normalized)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Unsupported Content-Type");
        }
    }

    private String normalizeContentType(String contentType) {
        if (contentType == null) {
            return null;
        }
        String trimmed = contentType.trim();
        if (trimmed.isEmpty()) {
            return null;
        }
        int semi = trimmed.indexOf(';');
        if (semi >= 0) {
            trimmed = trimmed.substring(0, semi);
        }
        return trimmed.trim().toLowerCase();
    }

    @PutMapping("/{projectId}/assets/{assetId}")
    public ResponseEntity<Asset> updateAsset(@PathVariable UUID projectId, @PathVariable UUID assetId, @RequestBody UpdateAssetRequest request) {
        Asset asset = projectService.updateAsset(assetId, request);
        return ResponseEntity.ok(asset);
    }

    @GetMapping("/{id}/timeline")
    public ResponseEntity<TimelineResponse> getTimeline(@PathVariable UUID id) {
        TimelineResponse timeline = projectService.getSmartTimeline(id);
        return ResponseEntity.ok(timeline);
    }

    @GetMapping("/{id}/script")
    public ResponseEntity<Map<String, Object>> getScript(@PathVariable UUID id) {
        Project project = projectService.getProject(id);
        Map<String, Object> body = new HashMap<>();
        body.put("projectId", project.getId().toString());
        body.put("status", project.getStatus() == null ? null : project.getStatus().name());
        body.put("scriptContent", project.getScriptContent());
        return ResponseEntity.ok(body);
    }

    @PostMapping("/{id}/script")
    public ResponseEntity<Map<String, Object>> generateScript(@PathVariable UUID id) {
        String taskId = projectService.generateScript(id);
        Project project = projectService.getProject(id);
        Map<String, Object> body = new HashMap<>();
        body.put("projectId", project.getId().toString());
        body.put("taskId", taskId);
        body.put("status", project.getStatus() == null ? ProjectStatus.SCRIPT_GENERATING.name() : project.getStatus().name());
        body.put("scriptContent", project.getScriptContent());
        return ResponseEntity.accepted().body(body);
    }

    @PutMapping(value = "/{id}/script", consumes = "text/plain")
    public ResponseEntity<Void> updateScript(
            @PathVariable UUID id, 
            @RequestBody(required = false) String scriptContent,
            @RequestHeader(value = "X-User-Id", required = false) Long userId) {
        if (scriptContent == null) {
            return ResponseEntity.badRequest().build();
        }
        projectService.updateScriptContent(id, scriptContent, userId);
        return ResponseEntity.accepted().build();
    }

    @PostMapping("/{id}/audio")
    public ResponseEntity<Void> generateAudio(@PathVariable UUID id, @RequestBody(required = false) String scriptContent) {
        if (scriptContent == null) {
            Project p = projectService.getProject(id);
            JsonNode node = p.getScriptContent();
            if (node != null) {
                scriptContent = node.isTextual() ? node.asText() : node.toString();
            }
        }
        projectService.generateAudio(id, scriptContent);
        return ResponseEntity.accepted().build();
    }

    @PostMapping("/{id}/render")
    public ResponseEntity<Void> renderVideo(
            @PathVariable UUID id,
            @RequestHeader(value = "X-User-Id", required = false) Long userId) {
        projectService.retryRender(id, userId);
        return ResponseEntity.accepted().build();
    }

    @PostMapping("/dev/reset")
    public ResponseEntity<Void> resetAllData() {
        if (!devResetEnabled) {
            return ResponseEntity.notFound().build();
        }
        projectService.resetAllData();
        return ResponseEntity.noContent().build();
    }
}
