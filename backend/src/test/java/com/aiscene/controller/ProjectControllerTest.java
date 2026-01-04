package com.aiscene.controller;

import com.aiscene.dto.CreateProjectRequest;
import com.aiscene.dto.TimelineResponse;
import com.aiscene.entity.Asset;
import com.aiscene.entity.Project;
import com.aiscene.service.ProjectService;
import com.aiscene.service.StorageService;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.mock.web.MockMultipartFile;

import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class ProjectControllerTest {

    @Test
    void createProject_delegatesToService() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);

        CreateProjectRequest req = new CreateProjectRequest();
        Project project = Project.builder().id(UUID.randomUUID()).build();
        when(projectService.createProject(req)).thenReturn(project);

        var resp = controller.createProject(req);

        assertThat(resp.getStatusCode().value()).isEqualTo(200);
        assertThat(resp.getBody()).isSameAs(project);
    }

    @Test
    void getProject_delegatesToService() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);

        UUID id = UUID.randomUUID();
        Project project = Project.builder().id(id).build();
        when(projectService.getProject(id)).thenReturn(project);

        var resp = controller.getProject(id);

        assertThat(resp.getStatusCode().value()).isEqualTo(200);
        assertThat(resp.getBody()).isSameAs(project);
    }

    @Test
    void uploadAsset_delegatesToService() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);

        UUID id = UUID.randomUUID();
        MockMultipartFile file = new MockMultipartFile("file", "a.txt", "text/plain", "x".getBytes());
        Asset asset = Asset.builder().id(UUID.randomUUID()).build();
        when(projectService.uploadAsset(id, file)).thenReturn(asset);

        var resp = controller.uploadAsset(id, file);

        assertThat(resp.getStatusCode().value()).isEqualTo(200);
        assertThat(resp.getBody()).isSameAs(asset);
    }

    @Test
    void getTimeline_delegatesToService() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);

        UUID id = UUID.randomUUID();
        TimelineResponse timeline = TimelineResponse.builder().projectId(id.toString()).assets(List.of()).build();
        when(projectService.getSmartTimeline(id)).thenReturn(timeline);

        var resp = controller.getTimeline(id);

        assertThat(resp.getStatusCode().value()).isEqualTo(200);
        assertThat(resp.getBody()).isSameAs(timeline);
    }

    @Test
    void generateScript_returnsAccepted() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);

        UUID id = UUID.randomUUID();
        when(projectService.generateScript(id)).thenReturn("task");
        when(projectService.getProject(id)).thenReturn(Project.builder().id(id).build());

        var resp = controller.generateScript(id);

        assertThat(resp.getStatusCode().value()).isEqualTo(202);
        verify(projectService).generateScript(id);
    }

    @Test
    void generateAudio_usesRequestBodyWhenProvided() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);

        UUID id = UUID.randomUUID();

        var resp = controller.generateAudio(id, "s");

        assertThat(resp.getStatusCode().value()).isEqualTo(202);
        verify(projectService).generateAudio(id, "s");
    }

    @Test
    void generateAudio_fallsBackToProjectScriptWhenNull() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);

        UUID id = UUID.randomUUID();
        Project project = Project.builder().id(id).scriptContent("s").build();
        when(projectService.getProject(id)).thenReturn(project);

        var resp = controller.generateAudio(id, null);

        assertThat(resp.getStatusCode().value()).isEqualTo(202);
        verify(projectService).generateAudio(id, "s");
    }

    @Test
    void renderVideo_returnsAccepted() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);

        UUID id = UUID.randomUUID();

        var resp = controller.renderVideo(id);

        assertThat(resp.getStatusCode().value()).isEqualTo(202);
        verify(projectService).renderVideo(id);
    }
}
