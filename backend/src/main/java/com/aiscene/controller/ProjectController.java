package com.aiscene.controller;

import com.aiscene.dto.CreateProjectRequest;
import com.aiscene.dto.TimelineResponse;
import com.aiscene.entity.Asset;
import com.aiscene.entity.Project;
import com.aiscene.service.ProjectService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.UUID;

@RestController
@RequestMapping("/v1/projects")
@RequiredArgsConstructor
@CrossOrigin(origins = "*") // Allow all for MVP dev
public class ProjectController {

    private final ProjectService projectService;

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

    @PostMapping("/{id}/assets")
    public ResponseEntity<Asset> uploadAsset(@PathVariable UUID id, @RequestParam("file") MultipartFile file) {
        Asset asset = projectService.uploadAsset(id, file);
        return ResponseEntity.ok(asset);
    }
    
    @GetMapping("/{id}/timeline")
    public ResponseEntity<TimelineResponse> getTimeline(@PathVariable UUID id) {
        TimelineResponse timeline = projectService.getSmartTimeline(id);
        return ResponseEntity.ok(timeline);
    }

    @PostMapping("/{id}/script")
    public ResponseEntity<Void> generateScript(@PathVariable UUID id) {
        projectService.generateScript(id);
        return ResponseEntity.accepted().build();
    }

    @PostMapping("/{id}/audio")
    public ResponseEntity<Void> generateAudio(@PathVariable UUID id, @RequestBody(required = false) String scriptContent) {
        // If scriptContent is null, service will pull from DB? No, current impl expects it.
        // Let's assume frontend sends it.
        if (scriptContent == null) {
            // Fallback fetch from DB if needed, but for now expect it
            // Or better: fetch project.getScriptContent() inside service if arg is null.
            // My service implementation: `taskQueueService.submitAudioGenerationTask(projectId, scriptContent);`
            // So if null, it will fail or generate silence.
            // Let's force frontend to send it for now (confirming edits).
            // Or better:
            Project p = projectService.getProject(id);
            scriptContent = p.getScriptContent(); 
        }
        projectService.generateAudio(id, scriptContent);
        return ResponseEntity.accepted().build();
    }

    @PostMapping("/{id}/render")
    public ResponseEntity<Void> renderVideo(@PathVariable UUID id) {
        projectService.renderVideo(id);
        return ResponseEntity.accepted().build();
    }
}
