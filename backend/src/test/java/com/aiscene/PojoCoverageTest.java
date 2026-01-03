package com.aiscene;

import com.aiscene.dto.AnalyzeTaskDto;
import com.aiscene.dto.CreateProjectRequest;
import com.aiscene.dto.TimelineResponse;
import com.aiscene.entity.Asset;
import com.aiscene.entity.Project;
import com.aiscene.entity.ProjectStatus;
import com.aiscene.entity.RenderJob;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

class PojoCoverageTest {

    @Test
    void lombokDataAndBuilders_areCovered() {
        CreateProjectRequest req0 = new CreateProjectRequest();
        assertThat(req0.getUserId()).isNull();
        assertThat(req0.getTitle()).isNull();
        assertThat(req0.getHouseInfo()).isNull();
        assertThat(req0.toString()).contains("CreateProjectRequest");

        CreateProjectRequest req = new CreateProjectRequest();
        req.setUserId(1L);
        req.setTitle("t");
        req.setHouseInfo(Map.of("room", 2));
        assertThat(req.getUserId()).isEqualTo(1L);
        assertThat(req.getTitle()).isEqualTo("t");
        assertThat(req.getHouseInfo()).containsEntry("room", 2);
        assertThat(req.equals(req)).isTrue();
        assertThat(req.equals(null)).isFalse();
        assertThat(req.equals("x")).isFalse();
        assertThat(req.equals(req0)).isFalse();
        assertThat(req.hashCode()).isNotZero();

        AnalyzeTaskDto dto0 = new AnalyzeTaskDto();
        assertThat(dto0.getProject_id()).isNull();
        dto0.setProject_id("p");
        dto0.setAsset_id("a");
        dto0.setVideo_url("v");
        assertThat(dto0.toString()).contains("project_id");

        AnalyzeTaskDto dto = AnalyzeTaskDto.builder()
                .project_id("p")
                .asset_id("a")
                .video_url("v")
                .build();
        assertThat(dto.getProject_id()).isEqualTo("p");
        assertThat(dto.getAsset_id()).isEqualTo("a");
        assertThat(dto.getVideo_url()).isEqualTo("v");
        assertThat(dto.toString()).contains("project_id");
        assertThat(dto.equals(dto0)).isTrue();
        assertThat(dto.equals(AnalyzeTaskDto.builder().project_id("p").asset_id("a").video_url("x").build())).isFalse();
        assertThat(dto.equals(null)).isFalse();
        assertThat(dto.equals("x")).isFalse();
        assertThat(dto.hashCode()).isNotZero();

        UUID projectId = UUID.randomUUID();
        var houseInfo = new ObjectMapper().createObjectNode().put("room", 2);
        LocalDateTime now = LocalDateTime.now();

        Project project = Project.builder()
                .id(projectId)
                .userId(2L)
                .title("p")
                .houseInfo(houseInfo)
                .status(ProjectStatus.DRAFT)
                .scriptContent("s")
                .finalVideoUrl("u")
                .createdAt(now)
                .build();
        assertThat(project.getStatus()).isEqualTo(ProjectStatus.DRAFT);
        assertThat(project.hashCode()).isNotZero();
        assertThat(project.toString()).contains("Project");

        Project project2 = new Project();
        project2.setId(projectId);
        project2.setUserId(2L);
        project2.setTitle("p");
        project2.setHouseInfo(houseInfo);
        project2.setStatus(ProjectStatus.DRAFT);
        project2.setScriptContent("s");
        project2.setFinalVideoUrl("u");
        project2.setCreatedAt(now);
        assertThat(project2.equals(project)).isTrue();
        assertThat(project2.equals(Project.builder().id(projectId).build())).isFalse();
        assertThat(project2.equals(null)).isFalse();
        assertThat(project2.equals("x")).isFalse();

        UUID assetId = UUID.randomUUID();
        Asset asset = Asset.builder()
                .id(assetId)
                .project(project)
                .ossUrl("oss")
                .duration(1.0)
                .sceneLabel("客厅")
                .sceneScore(0.9)
                .userLabel("x")
                .sortOrder(1)
                .isDeleted(false)
                .build();
        assertThat(asset.getProject()).isSameAs(project);
        assertThat(asset.getOssUrl()).isEqualTo("oss");
        assertThat(asset.getIsDeleted()).isFalse();
        asset.setIsDeleted(true);
        assertThat(asset.getIsDeleted()).isTrue();
        assertThat(asset.toString()).contains("Asset");
        assertThat(asset.equals(asset)).isTrue();
        assertThat(asset.equals(null)).isFalse();
        assertThat(asset.equals("x")).isFalse();
        assertThat(asset.equals(Asset.builder().id(assetId).build())).isFalse();
        assertThat(asset.hashCode()).isNotZero();

        Asset asset2 = new Asset();
        asset2.setId(assetId);
        asset2.setProject(project);
        asset2.setOssUrl("oss");
        asset2.setDuration(1.0);
        asset2.setSceneLabel("客厅");
        asset2.setSceneScore(0.9);
        asset2.setUserLabel("x");
        asset2.setSortOrder(1);
        asset2.setIsDeleted(true);
        assertThat(asset2.equals(asset)).isTrue();

        UUID jobId = UUID.randomUUID();
        RenderJob job = RenderJob.builder()
                .id(jobId)
                .project(project)
                .progress(10)
                .errorLog("e")
                .build();
        assertThat(job.getProgress()).isEqualTo(10);
        assertThat(job.equals(RenderJob.builder().id(job.getId()).build())).isFalse();
        assertThat(job.equals(job)).isTrue();
        assertThat(job.equals(null)).isFalse();
        assertThat(job.equals("x")).isFalse();
        assertThat(job.hashCode()).isNotZero();
        assertThat(job.toString()).contains("RenderJob");

        RenderJob job2 = new RenderJob();
        job2.setId(jobId);
        job2.setProject(project);
        job2.setProgress(10);
        job2.setErrorLog("e");
        assertThat(job2.equals(job)).isTrue();

        TimelineResponse timeline = TimelineResponse.builder()
                .projectId(project.getId().toString())
                .projectTitle(project.getTitle())
                .assets(List.of(asset))
                .scriptContent(project.getScriptContent())
                .build();
        assertThat(timeline.getAssets()).hasSize(1);
        assertThat(timeline.toString()).contains("projectId");
        assertThat(timeline.equals(timeline)).isTrue();
        assertThat(timeline.equals(null)).isFalse();
        assertThat(timeline.equals("x")).isFalse();
        assertThat(timeline.hashCode()).isNotZero();

        TimelineResponse timeline2 = TimelineResponse.builder()
                .projectId(project.getId().toString())
                .projectTitle(project.getTitle())
                .assets(new ArrayList<>(List.of(asset)))
                .scriptContent(project.getScriptContent())
                .build();
        assertThat(timeline2.equals(timeline)).isTrue();
        assertThat(timeline2.equals(TimelineResponse.builder().projectId("x").build())).isFalse();

        assertThat(ProjectStatus.valueOf("DRAFT")).isEqualTo(ProjectStatus.DRAFT);
        assertThat(ProjectStatus.values()).isNotEmpty();
    }
}
