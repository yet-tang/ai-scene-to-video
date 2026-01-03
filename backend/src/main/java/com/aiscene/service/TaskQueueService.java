package com.aiscene.service;

import com.aiscene.dto.AnalyzeTaskDto;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.MDC;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;
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

            Map<String, Object> headers = new HashMap<>();
            headers.put("lang", "py");
            headers.put("task", taskName);
            headers.put("id", taskId);
            headers.put("root_id", taskId);
            headers.put("parent_id", null);
            headers.put("group", null);
            headers.put("retries", 0);
            headers.put("timelimit", Arrays.asList(null, null));
            headers.put("argsrepr", Arrays.toString(args));
            headers.put("kwargsrepr", "{}");

            String requestId = MDC.get("request_id");
            if (requestId != null) {
                headers.put("request_id", requestId);
            }
            String userId = MDC.get("user_id");
            if (userId != null) {
                headers.put("user_id", userId);
            }

            Map<String, Object> embed = new HashMap<>();
            embed.put("callbacks", null);
            embed.put("errbacks", null);
            embed.put("chain", null);
            embed.put("chord", null);

            Object[] bodyTuple = new Object[]{Arrays.asList(args), new HashMap<>(), embed};
            String bodyJson = objectMapper.writeValueAsString(bodyTuple);
            String bodyBase64 = Base64.getEncoder().encodeToString(bodyJson.getBytes(StandardCharsets.UTF_8));

            Map<String, Object> properties = new HashMap<>();
            properties.put("correlation_id", taskId);
            properties.put("reply_to", UUID.randomUUID().toString());
            properties.put("delivery_mode", 2);
            properties.put("delivery_tag", UUID.randomUUID().toString());
            properties.put("priority", 0);
            properties.put("body_encoding", "base64");
            Map<String, Object> deliveryInfo = new HashMap<>();
            deliveryInfo.put("exchange", "");
            deliveryInfo.put("routing_key", QUEUE_NAME);
            properties.put("delivery_info", deliveryInfo);

            Map<String, Object> message = new HashMap<>();
            message.put("body", bodyBase64);
            message.put("content-encoding", "utf-8");
            message.put("content-type", "application/json");
            message.put("headers", headers);
            message.put("properties", properties);

            String jsonMessage = objectMapper.writeValueAsString(message);
            redisTemplate.opsForList().leftPush(QUEUE_NAME, jsonMessage);
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize task message for {}", taskName, e);
            throw new RuntimeException("Failed to submit task", e);
        }
    }
}
