package com.aiscene.controller;

import com.aiscene.dto.CreateProjectRequest;
import com.aiscene.entity.Asset;
import com.aiscene.entity.Project;
import com.aiscene.service.ProjectService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.UUID;

@RestController
@RequestMapping("/api/v1/projects")
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
}
