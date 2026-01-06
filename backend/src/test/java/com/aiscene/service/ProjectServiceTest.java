package com.aiscene.service;

import com.aiscene.dto.AssetConfirmRequest;
import com.aiscene.dto.CreateProjectRequest;
import com.aiscene.dto.TimelineResponse;
import com.aiscene.dto.UpdateAssetRequest;
import com.aiscene.entity.Asset;
import com.aiscene.entity.Project;
import com.aiscene.entity.ProjectStatus;
import com.aiscene.repository.AssetRepository;
import com.aiscene.repository.ProjectRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ProjectServiceTest {

    @Mock
    private ProjectRepository projectRepository;

    @Mock
    private AssetRepository assetRepository;

    @Mock
    private StorageService storageService;

    @Mock
    private TaskQueueService taskQueueService;

    @Mock
    private ObjectMapper objectMapper;

    @Mock
    private JdbcTemplate jdbcTemplate;

    @InjectMocks
    private ProjectService projectService;

    @Test
    void createProject_savesDraftWithJsonHouseInfo() {
        CreateProjectRequest request = new CreateProjectRequest();
        request.setUserId(123L);
        request.setTitle("t");
        Map<String, Object> houseInfo = new HashMap<>();
        houseInfo.put("room", 2);
        request.setHouseInfo(houseInfo);

        var jsonNode = new ObjectMapper().createObjectNode().put("room", 2);
        when(objectMapper.valueToTree(houseInfo)).thenReturn(jsonNode);

        Project saved = Project.builder().id(UUID.randomUUID()).userId(123L).title("t").houseInfo(jsonNode).status(ProjectStatus.DRAFT).build();
        when(projectRepository.save(any(Project.class))).thenReturn(saved);

        Project result = projectService.createProject(request);

        ArgumentCaptor<Project> captor = ArgumentCaptor.forClass(Project.class);
        verify(projectRepository).save(captor.capture());
        Project toSave = captor.getValue();
        assertThat(toSave.getUserId()).isEqualTo(123L);
        assertThat(toSave.getTitle()).isEqualTo("t");
        assertThat(toSave.getHouseInfo()).isEqualTo(jsonNode);
        assertThat(toSave.getStatus()).isEqualTo(ProjectStatus.DRAFT);
        assertThat(result).isSameAs(saved);
    }

    @Test
    void getSmartTimeline_sortsByScenePriorityWhenAnalyzed() {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).title("p").build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));

        Asset a1 = Asset.builder().id(UUID.randomUUID()).sceneLabel("客厅").sortOrder(0).build();
        Asset a2 = Asset.builder().id(UUID.randomUUID()).sceneLabel("厨房").sortOrder(0).build();
        Asset a3 = Asset.builder().id(UUID.randomUUID()).sceneLabel("小区门头").sortOrder(0).build();
        List<Asset> assets = new ArrayList<>(List.of(a1, a2, a3));
        when(assetRepository.findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(projectId)).thenReturn(assets);

        TimelineResponse timeline = projectService.getSmartTimeline(projectId);

        assertThat(timeline.getAssets()).containsExactly(a3, a1, a2);
    }

    @Test
    void getSmartTimeline_doesNotSortWhenNoAnalysis() {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).title("p").build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));

        Asset a1 = Asset.builder().id(UUID.randomUUID()).sceneLabel(null).build();
        Asset a2 = Asset.builder().id(UUID.randomUUID()).sceneLabel(null).build();
        List<Asset> assets = new ArrayList<>(List.of(a1, a2));
        when(assetRepository.findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(projectId)).thenReturn(assets);

        TimelineResponse timeline = projectService.getSmartTimeline(projectId);

        assertThat(timeline.getAssets()).containsExactly(a1, a2);
    }

    @Test
    void generateScript_submitsTaskWithHouseInfoAndTimelineData() {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).houseInfo(new ObjectMapper().createObjectNode().put("x", 1)).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));

        Asset asset = Asset.builder()
                .id(UUID.randomUUID())
                .sceneLabel("客厅")
                .sceneScore(0.9)
                .ossUrl("u")
                .duration(3.0)
                .build();
        when(assetRepository.findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(projectId)).thenReturn(List.of(asset));

        Object houseInfoObj = Map.of("x", 1);
        when(objectMapper.convertValue(eq(project.getHouseInfo()), eq(Object.class))).thenReturn(houseInfoObj);

        projectService.generateScript(projectId);

        ArgumentCaptor<List<Object>> timelineCaptor = ArgumentCaptor.forClass(List.class);
        verify(taskQueueService).submitScriptGenerationTask(eq(projectId), eq(houseInfoObj), timelineCaptor.capture());
        List<Object> timelineData = timelineCaptor.getValue();
        assertThat(timelineData).hasSize(1);
        assertThat(timelineData.get(0)).isInstanceOf(Map.class);
        Map<?, ?> map = (Map<?, ?>) timelineData.get(0);
        assertThat(map.get("id")).isEqualTo(asset.getId().toString());
        assertThat(map.get("scene_label")).isEqualTo("客厅");
        assertThat(map.get("scene_score")).isEqualTo(0.9);
        assertThat(map.get("oss_url")).isEqualTo("u");
        assertThat(map.get("duration")).isEqualTo(3.0);
    }

    @Test
    void generateAudio_updatesScriptAndSubmitsTask() {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(projectRepository.save(any(Project.class))).thenAnswer(invocation -> invocation.getArgument(0));

        projectService.generateAudio(projectId, "s");

        ArgumentCaptor<Project> captor = ArgumentCaptor.forClass(Project.class);
        verify(projectRepository).save(captor.capture());
        assertThat(captor.getValue().getScriptContent()).isEqualTo("s");
        assertThat(captor.getValue().getStatus()).isEqualTo(ProjectStatus.AUDIO_GENERATING);
        verify(taskQueueService).submitAudioGenerationTask(projectId, "s");
    }

    @Test
    void renderVideo_submitsRenderPipelineTask() {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).status(ProjectStatus.SCRIPT_GENERATED).scriptContent("content").build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(projectRepository.updateStatusIfIn(eq(projectId), any(), eq(ProjectStatus.RENDERING))).thenReturn(1);

        Asset a1 = Asset.builder().id(UUID.randomUUID()).ossUrl("u1").duration(1.0).build();
        Asset a2 = Asset.builder().id(UUID.randomUUID()).ossUrl("u2").duration(2.0).build();
        when(assetRepository.findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(projectId)).thenReturn(List.of(a1, a2));

        projectService.renderVideo(projectId);

        verify(taskQueueService).submitRenderPipelineTask(eq(projectId), eq("content"), any(List.class));
        verify(projectRepository).updateStatusIfIn(eq(projectId), any(), eq(ProjectStatus.RENDERING));
    }

    @Test
    void uploadAsset_updatesStatusWhenDraftAndSubmitsAnalysisTask() throws java.io.IOException {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).status(ProjectStatus.DRAFT).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));

        when(storageService.uploadFileAndReturnObject(any())).thenReturn(new StorageService.UploadedObject("k1", "pub1"));
        when(storageService.getBucketName()).thenReturn("b");

        when(assetRepository.save(any(Asset.class))).thenAnswer(invocation -> {
            Asset a = invocation.getArgument(0);
            a.setId(UUID.randomUUID());
            return a;
        });

        var file = new org.springframework.mock.web.MockMultipartFile("file", "x.txt", "text/plain", "x".getBytes());
        Asset saved = projectService.uploadAsset(projectId, file);

        verify(projectRepository, times(2)).save(project);
        assertThat(project.getStatus()).isEqualTo(ProjectStatus.ANALYZING);
        
        ArgumentCaptor<String> urlCaptor = ArgumentCaptor.forClass(String.class);
        verify(taskQueueService).submitAnalysisTask(eq(projectId), eq(saved.getId()), urlCaptor.capture());
        String capturedUrl = urlCaptor.getValue();
        assertThat(capturedUrl).isEqualTo("pub1");

        ArgumentCaptor<Asset> assetCaptor = ArgumentCaptor.forClass(Asset.class);
        verify(assetRepository).save(assetCaptor.capture());
        assertThat(assetCaptor.getValue().getStorageType()).isEqualTo("S3");
        assertThat(assetCaptor.getValue().getStorageBucket()).isEqualTo("b");
        assertThat(assetCaptor.getValue().getStorageKey()).isEqualTo("k1");
    }

    @Test
    void uploadAsset_advancesStatusWhenUploading() throws java.io.IOException {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).status(ProjectStatus.UPLOADING).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));

        when(storageService.uploadFileAndReturnObject(any())).thenReturn(new StorageService.UploadedObject("k1", "pub1"));
        when(storageService.getBucketName()).thenReturn("b");
        when(assetRepository.save(any(Asset.class))).thenAnswer(invocation -> invocation.getArgument(0));
        var file = new org.springframework.mock.web.MockMultipartFile("file", "x.txt", "text/plain", "x".getBytes());

        projectService.uploadAsset(projectId, file);

        verify(projectRepository).save(project);
        assertThat(project.getStatus()).isEqualTo(ProjectStatus.ANALYZING);
    }

    @Test
    void getProject_throwsWhenMissing() {
        UUID projectId = UUID.randomUUID();
        when(projectRepository.findById(projectId)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> projectService.getProject(projectId))
                .isInstanceOf(RuntimeException.class)
                .hasMessageContaining("Project not found");
    }

    @Test
    void confirmAsset_updatesStatusAndSubmitsAnalysisTaskWhenDraft() {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).status(ProjectStatus.DRAFT).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));

        AssetConfirmRequest request = new AssetConfirmRequest();
        request.setObjectKey("k");
        when(storageService.getPublicUrl("k")).thenReturn("pub");
        when(storageService.getBucketName()).thenReturn("b");
        when(assetRepository.findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(projectId)).thenReturn(List.of());
        when(assetRepository.save(any(Asset.class))).thenAnswer(invocation -> {
            Asset a = invocation.getArgument(0);
            a.setId(UUID.randomUUID());
            return a;
        });

        Asset saved = projectService.confirmAsset(projectId, request);

        assertThat(saved.getOssUrl()).isEqualTo("pub");
        assertThat(saved.getStorageType()).isEqualTo("S3");
        assertThat(saved.getStorageBucket()).isEqualTo("b");
        assertThat(saved.getStorageKey()).isEqualTo("k");
        assertThat(saved.getDuration()).isEqualTo(0.0);
        assertThat(saved.getSortOrder()).isEqualTo(0);
        assertThat(project.getStatus()).isEqualTo(ProjectStatus.ANALYZING);
        verify(projectRepository, times(2)).save(project);
        verify(taskQueueService).submitAnalysisTask(projectId, saved.getId(), "pub");
    }

    @Test
    void confirmAsset_doesNotUpdateStatusWhenAlreadyAnalyzing() {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).status(ProjectStatus.ANALYZING).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));

        AssetConfirmRequest request = new AssetConfirmRequest();
        request.setObjectKey("k");
        when(storageService.getPublicUrl("k")).thenReturn("pub");
        when(assetRepository.findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(projectId)).thenReturn(List.of());
        when(assetRepository.save(any(Asset.class))).thenAnswer(invocation -> {
            Asset a = invocation.getArgument(0);
            a.setId(UUID.randomUUID());
            return a;
        });

        Asset saved = projectService.confirmAsset(projectId, request);

        assertThat(project.getStatus()).isEqualTo(ProjectStatus.ANALYZING);
        verify(projectRepository, never()).save(project);
        verify(taskQueueService).submitAnalysisTask(projectId, saved.getId(), "pub");
    }

    @Test
    void updateAsset_updatesUserLabelSceneLabelAndSortOrder() {
        UUID assetId = UUID.randomUUID();
        Asset asset = Asset.builder().id(assetId).sceneLabel("厨房").sortOrder(1).build();
        when(assetRepository.findById(assetId)).thenReturn(Optional.of(asset));
        when(assetRepository.save(any(Asset.class))).thenAnswer(invocation -> invocation.getArgument(0));

        UpdateAssetRequest req = UpdateAssetRequest.builder().userLabel("客厅").sortOrder(2).build();
        Asset updated = projectService.updateAsset(assetId, req);

        assertThat(updated.getUserLabel()).isEqualTo("客厅");
        assertThat(updated.getSceneLabel()).isEqualTo("客厅");
        assertThat(updated.getSortOrder()).isEqualTo(2);
        verify(assetRepository).save(asset);
    }

    @Test
    void updateScriptContent_throwsWhenCompleted() {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).status(ProjectStatus.COMPLETED).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));

        assertThatThrownBy(() -> projectService.updateScriptContent(projectId, "s"))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("completed");
        verify(projectRepository, never()).save(any(Project.class));
    }

    @Test
    void resetAllData_truncatesTables() {
        projectService.resetAllData();
        verify(jdbcTemplate).execute("TRUNCATE TABLE render_jobs, assets, projects RESTART IDENTITY CASCADE");
    }

    @Test
    void updateScriptContent_throwsWhenProcessing() {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).status(ProjectStatus.AUDIO_GENERATING).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));

        assertThatThrownBy(() -> projectService.updateScriptContent(projectId, "s"))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("processing");
        verify(projectRepository, never()).save(any(Project.class));
    }

    @Test
    void updateScriptContent_updatesStatusAndSaves() {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).status(ProjectStatus.DRAFT).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(projectRepository.save(any(Project.class))).thenAnswer(invocation -> invocation.getArgument(0));

        projectService.updateScriptContent(projectId, "s");

        assertThat(project.getScriptContent()).isEqualTo("s");
        assertThat(project.getStatus()).isEqualTo(ProjectStatus.SCRIPT_GENERATED);
        verify(projectRepository).save(project);
    }

    @Test
    void renderVideo_throwsWhenScriptEmpty() {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).status(ProjectStatus.SCRIPT_GENERATED).scriptContent(" ").build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));

        assertThatThrownBy(() -> projectService.renderVideo(projectId))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("empty");
        verify(projectRepository, never()).updateStatusIfIn(any(), any(), any());
    }

    @Test
    void renderVideo_throwsWhenNoAssets() {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).status(ProjectStatus.SCRIPT_GENERATED).scriptContent("c").build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(assetRepository.findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(projectId)).thenReturn(List.of());

        assertThatThrownBy(() -> projectService.renderVideo(projectId))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("No assets");
        verify(projectRepository, never()).updateStatusIfIn(any(), any(), any());
    }

    @Test
    void renderVideo_throwsProcessingWhenStatusUpdateRejectedButAlreadyRendering() {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).status(ProjectStatus.RENDERING).scriptContent("c").build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(assetRepository.findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(projectId)).thenReturn(List.of(
                Asset.builder().id(UUID.randomUUID()).ossUrl("u").duration(1.0).build()
        ));
        when(projectRepository.updateStatusIfIn(eq(projectId), any(), eq(ProjectStatus.RENDERING))).thenReturn(0);

        assertThatThrownBy(() -> projectService.renderVideo(projectId))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("processing");
    }

    @Test
    void renderVideo_throwsNotReadyWhenStatusUpdateRejected() {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).status(ProjectStatus.DRAFT).scriptContent("c").build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(assetRepository.findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(projectId)).thenReturn(List.of(
                Asset.builder().id(UUID.randomUUID()).ossUrl("u").duration(1.0).build()
        ));
        when(projectRepository.updateStatusIfIn(eq(projectId), any(), eq(ProjectStatus.RENDERING))).thenReturn(0);

        assertThatThrownBy(() -> projectService.renderVideo(projectId))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("not ready");
    }

    @Test
    void uploadAsset_usesStorageServiceAndWritesStorageFields() throws java.io.IOException {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).status(ProjectStatus.DRAFT).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));

        org.springframework.web.multipart.MultipartFile file = org.mockito.Mockito.mock(org.springframework.web.multipart.MultipartFile.class);
        when(storageService.getBucketName()).thenReturn("b1");
        when(storageService.uploadFileAndReturnObject(file)).thenReturn(new StorageService.UploadedObject("k1", "https://pub/u1"));

        when(assetRepository.save(any(Asset.class))).thenAnswer(invocation -> {
            Asset a = invocation.getArgument(0);
            a.setId(UUID.randomUUID());
            return a;
        });

        Asset saved = projectService.uploadAsset(projectId, file);

        assertThat(saved.getOssUrl()).isEqualTo("https://pub/u1");
        assertThat(saved.getStorageType()).isEqualTo("S3");
        assertThat(saved.getStorageBucket()).isEqualTo("b1");
        assertThat(saved.getStorageKey()).isEqualTo("k1");

        verify(storageService).uploadFileAndReturnObject(file);
        verify(taskQueueService).submitAnalysisTask(projectId, saved.getId(), "https://pub/u1");
        assertThat(project.getStatus()).isEqualTo(ProjectStatus.ANALYZING);
    }

    @Test
    void uploadAssetLocal_usesStorageServiceAndSortOrder() throws java.io.IOException {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).status(ProjectStatus.DRAFT).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(assetRepository.findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(projectId)).thenReturn(List.of(
                Asset.builder().id(UUID.randomUUID()).build(),
                Asset.builder().id(UUID.randomUUID()).build()
        ));
        when(storageService.getBucketName()).thenReturn("b1");
        when(storageService.uploadFileAndReturnObject(any())).thenReturn(new StorageService.UploadedObject("k1", "https://pub/u1"));
        when(assetRepository.save(any(Asset.class))).thenAnswer(invocation -> {
            Asset a = invocation.getArgument(0);
            a.setId(UUID.randomUUID());
            return a;
        });

        var file = new org.springframework.mock.web.MockMultipartFile("file", "x.txt", "text/plain", "x".getBytes());
        Asset saved = projectService.uploadAssetLocal(projectId, file);

        assertThat(saved.getSortOrder()).isEqualTo(2);
        assertThat(saved.getOssUrl()).isEqualTo("https://pub/u1");
        assertThat(saved.getStorageType()).isEqualTo("S3");
        assertThat(saved.getStorageBucket()).isEqualTo("b1");
        assertThat(saved.getStorageKey()).isEqualTo("k1");
        assertThat(project.getStatus()).isEqualTo(ProjectStatus.ANALYZING);
    }

    @Test
    void uploadAssetLocal_submitsAnalysisTask() throws java.io.IOException {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).status(ProjectStatus.DRAFT).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(assetRepository.findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(projectId)).thenReturn(List.of());
        when(storageService.uploadFileAndReturnObject(any())).thenReturn(new StorageService.UploadedObject("k1", "https://pub/u1"));

        when(assetRepository.save(any(Asset.class))).thenAnswer(invocation -> {
            Asset a = invocation.getArgument(0);
            a.setId(UUID.randomUUID());
            return a;
        });

        var file = new org.springframework.mock.web.MockMultipartFile("file", "x.mp4", "video/mp4", "x".getBytes());
        Asset saved = projectService.uploadAssetLocal(projectId, file);

        verify(taskQueueService).submitAnalysisTask(projectId, saved.getId(), "https://pub/u1");
    }

    @Test
    void listProjects_callsCorrectRepositoryMethod() {
        Page<Project> page = org.mockito.Mockito.mock(Page.class);
        when(projectRepository.findAll(any(Pageable.class))).thenReturn(page);
        when(projectRepository.findAllByUserId(eq(1L), any(Pageable.class))).thenReturn(page);

        Page<Project> r0 = projectService.listProjects(null, 2, 10);
        Page<Project> r1 = projectService.listProjects(1L, 1, 10);

        assertThat(r0).isSameAs(page);
        assertThat(r1).isSameAs(page);
        verify(projectRepository).findAll(any(Pageable.class));
        verify(projectRepository).findAllByUserId(eq(1L), any(Pageable.class));
    }
}
