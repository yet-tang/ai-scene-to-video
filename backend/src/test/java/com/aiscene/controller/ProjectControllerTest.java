package com.aiscene.controller;

import com.aiscene.dto.CreateProjectRequest;
import com.aiscene.dto.PresignedUrlResponse;
import com.aiscene.dto.AssetConfirmRequest;
import com.aiscene.dto.TimelineResponse;
import com.aiscene.entity.Asset;
import com.aiscene.entity.Project;
import com.aiscene.entity.ProjectStatus;
import com.aiscene.dto.UpdateAssetRequest;
import com.aiscene.service.ProjectService;
import com.aiscene.service.StorageService;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.mockito.Mockito.never;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;

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
        MockMultipartFile file = new MockMultipartFile("file", "a.mp4", "video/mp4", "x".getBytes());
        Asset asset = Asset.builder().id(UUID.randomUUID()).build();
        when(projectService.uploadAsset(id, file)).thenReturn(asset);

        ReflectionTestUtils.setField(controller, "allowedContentTypes", List.of("video/mp4"));

        var resp = controller.uploadAsset(id, file);

        assertThat(resp.getStatusCode().value()).isEqualTo(200);
        assertThat(resp.getBody()).isSameAs(asset);
    }

    @Test
    void uploadAssetLocal_delegatesToService() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);

        UUID id = UUID.randomUUID();
        MockMultipartFile file = new MockMultipartFile("file", "a.mov", "video/quicktime", "x".getBytes());
        Asset asset = Asset.builder().id(UUID.randomUUID()).build();
        when(projectService.uploadAssetLocal(id, file)).thenReturn(asset);

        ReflectionTestUtils.setField(controller, "allowedContentTypes", List.of("video/quicktime"));

        var resp = controller.uploadAssetLocal(id, file);

        assertThat(resp.getStatusCode().value()).isEqualTo(200);
        assertThat(resp.getBody()).isSameAs(asset);
    }

    @Test
    void getPresignedUrl_delegatesToStorageService() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);

        UUID id = UUID.randomUUID();
        PresignedUrlResponse respBody = PresignedUrlResponse.builder()
                .uploadUrl("u")
                .publicUrl("p")
                .objectKey("k")
                .signedHeaders(java.util.Map.of())
                .build();
        ReflectionTestUtils.setField(controller, "allowedContentTypes", List.of("video/mp4"));
        when(storageService.generatePresignedUrl(any(String.class), eq("video/mp4"))).thenReturn(respBody);

        var resp = controller.getPresignedUrl(id, "a.mp4", "video/mp4");

        assertThat(resp.getStatusCode().value()).isEqualTo(200);
        assertThat(resp.getBody()).isSameAs(respBody);
        var keyCaptor = org.mockito.ArgumentCaptor.forClass(String.class);
        verify(storageService).generatePresignedUrl(keyCaptor.capture(), eq("video/mp4"));
        assertThat(keyCaptor.getValue()).contains("-a.mp4");
    }

    @Test
    void confirmAsset_delegatesToService() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);

        UUID id = UUID.randomUUID();
        AssetConfirmRequest req = new AssetConfirmRequest();
        req.setContentType("video/mp4");
        Asset asset = Asset.builder().id(UUID.randomUUID()).build();
        when(projectService.confirmAsset(id, req)).thenReturn(asset);

        ReflectionTestUtils.setField(controller, "allowedContentTypes", List.of("video/mp4"));

        var resp = controller.confirmAsset(id, req);

        assertThat(resp.getStatusCode().value()).isEqualTo(200);
        assertThat(resp.getBody()).isSameAs(asset);
    }

    @Test
    void getPresignedUrl_rejectsUnsupportedContentType() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);
        ReflectionTestUtils.setField(controller, "allowedContentTypes", List.of("video/mp4"));

        assertThatThrownBy(() -> controller.getPresignedUrl(UUID.randomUUID(), "a.mov", "video/quicktime"))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode().value()).isEqualTo(400));
    }

    @Test
    void confirmAsset_rejectsUnsupportedContentType() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);
        ReflectionTestUtils.setField(controller, "allowedContentTypes", List.of("video/mp4"));

        AssetConfirmRequest req = new AssetConfirmRequest();
        req.setContentType("video/quicktime");

        assertThatThrownBy(() -> controller.confirmAsset(UUID.randomUUID(), req))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode().value()).isEqualTo(400));
    }

    @Test
    void updateAsset_delegatesToService() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);

        UUID projectId = UUID.randomUUID();
        UUID assetId = UUID.randomUUID();
        UpdateAssetRequest req = new UpdateAssetRequest();
        Asset asset = Asset.builder().id(assetId).build();
        when(projectService.updateAsset(assetId, req)).thenReturn(asset);

        var resp = controller.updateAsset(projectId, assetId, req);

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
    void getScript_returnsFields() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);

        UUID id = UUID.randomUUID();
        Project project = Project.builder().id(id).status(ProjectStatus.SCRIPT_GENERATED).scriptContent("s").build();
        when(projectService.getProject(id)).thenReturn(project);

        var resp = controller.getScript(id);

        assertThat(resp.getStatusCode().value()).isEqualTo(200);
        assertThat(resp.getBody()).isNotNull();
        assertThat(resp.getBody().get("projectId")).isEqualTo(id.toString());
        assertThat(resp.getBody().get("status")).isEqualTo("SCRIPT_GENERATED");
        assertThat(resp.getBody().get("scriptContent")).isEqualTo("s");
    }

    @Test
    void updateScript_delegatesToService() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);

        UUID id = UUID.randomUUID();
        var resp = controller.updateScript(id, "s", null);

        assertThat(resp.getStatusCode().value()).isEqualTo(202);
        verify(projectService).updateScriptContent(id, "s", null);
    }

    @Test
    void updateScript_returnsBadRequestWhenNullBody() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);

        UUID id = UUID.randomUUID();
        var resp = controller.updateScript(id, null, null);

        assertThat(resp.getStatusCode().value()).isEqualTo(400);
    }

    @Test
    void renderVideo_returnsAccepted() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);

        UUID id = UUID.randomUUID();

        var resp = controller.renderVideo(id, null);

        assertThat(resp.getStatusCode().value()).isEqualTo(202);
        verify(projectService).retryRender(id, null);
    }

    @Test
    void listProjects_delegatesToService() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);
        
        Long userId = 123L;
        Project p = Project.builder().id(UUID.randomUUID()).title("t").build();
        org.springframework.data.domain.Page<Project> page = new org.springframework.data.domain.PageImpl<>(List.of(p));
        when(projectService.listProjects(userId, 1, 10)).thenReturn(page);
        
        var resp = controller.listProjects(userId, 1, 10);
        
        assertThat(resp.getStatusCode().value()).isEqualTo(200);
        assertThat(resp.getBody()).isNotNull();
        assertThat(resp.getBody().getContent()).hasSize(1);
        assertThat(resp.getBody().getContent().get(0).getId()).isEqualTo(p.getId());
        assertThat(resp.getBody().getContent().get(0).getTitle()).isEqualTo("t");
    }

    @Test
    void listProjects_allowsNullUserId() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);

        org.springframework.data.domain.Page<Project> page = org.springframework.data.domain.Page.empty();
        when(projectService.listProjects(null, 1, 10)).thenReturn(page);

        var resp = controller.listProjects(null, 1, 10);

        assertThat(resp.getStatusCode().value()).isEqualTo(200);
    }

    @Test
    void resetAllData_returns404WhenDisabled() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);

        var resp = controller.resetAllData();

        assertThat(resp.getStatusCode().value()).isEqualTo(404);
        verify(projectService, never()).resetAllData();
    }

    @Test
    void resetAllData_returnsNoContentWhenEnabled() {
        ProjectService projectService = Mockito.mock(ProjectService.class);
        StorageService storageService = Mockito.mock(StorageService.class);
        ProjectController controller = new ProjectController(projectService, storageService);
        ReflectionTestUtils.setField(controller, "devResetEnabled", true);

        var resp = controller.resetAllData();

        assertThat(resp.getStatusCode().value()).isEqualTo(204);
        verify(projectService).resetAllData();
    }
}
