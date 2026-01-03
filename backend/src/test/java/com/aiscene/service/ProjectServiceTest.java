package com.aiscene.service;

import com.aiscene.dto.CreateProjectRequest;
import com.aiscene.dto.TimelineResponse;
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
        assertThat(map.get("asset_id")).isEqualTo(asset.getId().toString());
        assertThat(map.get("scene_label")).isEqualTo("客厅");
        assertThat(map.get("scene_score")).isEqualTo(0.9);
        assertThat(map.get("oss_url")).isEqualTo("u");
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
        verify(taskQueueService).submitAudioGenerationTask(projectId, "s");
    }

    @Test
    void renderVideo_submitsRenderTaskWithAssetsAndAudioConvention() {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));

        Asset a1 = Asset.builder().ossUrl("u1").duration(1.0).build();
        Asset a2 = Asset.builder().ossUrl("u2").duration(2.0).build();
        when(assetRepository.findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(projectId)).thenReturn(List.of(a1, a2));

        projectService.renderVideo(projectId);

        ArgumentCaptor<List<Object>> assetsCaptor = ArgumentCaptor.forClass(List.class);
        verify(taskQueueService).submitRenderVideoTask(eq(projectId), assetsCaptor.capture(), eq("/tmp/" + projectId + ".mp3"));
        List<Object> payload = assetsCaptor.getValue();
        assertThat(payload).hasSize(2);
        Map<?, ?> first = (Map<?, ?>) payload.get(0);
        assertThat(first.get("oss_url")).isEqualTo("u1");
        assertThat(first.get("duration")).isEqualTo(1.0);
    }

    @Test
    void uploadAsset_updatesStatusWhenDraftAndSubmitsAnalysisTask() throws java.io.IOException {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).status(ProjectStatus.DRAFT).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));

        // Mock local file transfer to avoid real file system access issues in test environment or assume success
        // But since transferTo writes to disk, we might want to mock the file object itself more deeply or just verify flow.
        // Actually, since we changed implementation to write to local disk first, we need to handle that.
        // For unit test, we can't easily mock Paths.get or Files.createDirectories without PowerMock.
        // But we can verify that taskQueueService receives a file:// url.
        
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
        assertThat(capturedUrl).startsWith("file:///");
        assertThat(capturedUrl).endsWith(".txt");
    }

    @Test
    void uploadAsset_advancesStatusWhenUploading() throws java.io.IOException {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).status(ProjectStatus.UPLOADING).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));

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
}
