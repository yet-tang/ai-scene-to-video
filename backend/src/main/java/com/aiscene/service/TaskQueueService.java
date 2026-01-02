package com.aiscene.service;

import com.aiscene.dto.AnalyzeTaskDto;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class TaskQueueService {

    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;

    // Must match the queue name in Celery
    private static final String QUEUE_NAME = "celery"; 

    public void submitAnalysisTask(UUID projectId, UUID assetId, String videoUrl) {
        // ... existing implementation
        // Re-implementing just to keep context, but actually we should just add new methods
        // To avoid SearchReplace complexity on existing method, I will assume it's there and add new ones.
        // Wait, SearchReplace replaces the whole chunk.
        
        AnalyzeTaskDto taskDto = AnalyzeTaskDto.builder()
                .project_id(projectId.toString())
                .asset_id(assetId.toString())
                .video_url(videoUrl)
                .build();
        
        sendCeleryTask("tasks.analyze_video_task", new Object[]{taskDto.getProject_id(), taskDto.getAsset_id(), taskDto.getVideo_url()});
        log.info("Submitted analysis task for asset {}", assetId);
    }

    public void submitScriptGenerationTask(UUID projectId, Object houseInfo, java.util.List<Object> timelineData) {
        sendCeleryTask("tasks.generate_script_task", new Object[]{projectId.toString(), houseInfo, timelineData});
        log.info("Submitted script generation task for project {}", projectId);
    }

    public void submitAudioGenerationTask(UUID projectId, String scriptContent) {
        sendCeleryTask("tasks.generate_audio_task", new Object[]{projectId.toString(), scriptContent});
        log.info("Submitted audio generation task for project {}", projectId);
    }

    public void submitRenderVideoTask(UUID projectId, java.util.List<Object> timelineAssets, String audioPath) {
        sendCeleryTask("tasks.render_video_task", new Object[]{projectId.toString(), timelineAssets, audioPath});
        log.info("Submitted render video task for project {}", projectId);
    }

    private void sendCeleryTask(String taskName, Object[] args) {
        try {
            String taskId = UUID.randomUUID().toString();
            CeleryMessage message = new CeleryMessage(taskId, taskName, args);
            String jsonMessage = objectMapper.writeValueAsString(message);
            redisTemplate.opsForList().leftPush(QUEUE_NAME, jsonMessage);
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize task message for {}", taskName, e);
            throw new RuntimeException("Failed to submit task", e);
        }
    }

    // Inner class for Celery Message Structure
    // Using simple POJO to avoid Lombok issues in inner class for this snippet
    private static class CeleryMessage {
        public String id;
        public String task;
        public Object[] args;
        public Object kwargs = new Object();
        public int retries = 0;

        public CeleryMessage(String id, String task, Object[] args) {
            this.id = id;
            this.task = task;
            this.args = args;
        }
    }
}
