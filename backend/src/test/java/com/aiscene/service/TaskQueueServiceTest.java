package com.aiscene.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.Mockito;
import org.slf4j.MDC;
import org.springframework.data.redis.core.ListOperations;
import org.springframework.data.redis.core.StringRedisTemplate;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class TaskQueueServiceTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @AfterEach
    void tearDown() {
        MDC.clear();
    }

    @Test
    void submitAnalysisTask_includesMdcHeaders() throws Exception {
        StringRedisTemplate redisTemplate = Mockito.mock(StringRedisTemplate.class);
        ListOperations<String, String> listOps = Mockito.mock(ListOperations.class);
        when(redisTemplate.opsForList()).thenReturn(listOps);

        TaskQueueService service = new TaskQueueService(redisTemplate, objectMapper);

        MDC.put("request_id", "r1");
        MDC.put("user_id", "u1");

        UUID projectId = UUID.randomUUID();
        UUID assetId = UUID.randomUUID();
        service.submitAnalysisTask(projectId, assetId, "v");

        ArgumentCaptor<String> payloadCaptor = ArgumentCaptor.forClass(String.class);
        verify(listOps).leftPush(anyString(), payloadCaptor.capture());

        JsonNode json = objectMapper.readTree(payloadCaptor.getValue());
        assertThat(json.get("headers").get("task").asText()).isEqualTo("tasks.analyze_video_task");
        assertThat(json.get("headers").get("request_id").asText()).isEqualTo("r1");
        assertThat(json.get("headers").get("user_id").asText()).isEqualTo("u1");

        String body = json.get("body").asText();
        String decoded = new String(Base64.getDecoder().decode(body), StandardCharsets.UTF_8);
        JsonNode bodyJson = objectMapper.readTree(decoded);
        assertThat(bodyJson.get(0).get(0).asText()).isEqualTo(projectId.toString());
        assertThat(bodyJson.get(0).get(1).asText()).isEqualTo(assetId.toString());
        assertThat(bodyJson.get(0).get(2).asText()).isEqualTo("v");
    }

    @Test
    void submitScriptGenerationTask_serializesPayload() throws Exception {
        StringRedisTemplate redisTemplate = Mockito.mock(StringRedisTemplate.class);
        ListOperations<String, String> listOps = Mockito.mock(ListOperations.class);
        when(redisTemplate.opsForList()).thenReturn(listOps);

        TaskQueueService service = new TaskQueueService(redisTemplate, objectMapper);
        UUID projectId = UUID.randomUUID();

        service.submitScriptGenerationTask(projectId, Map.of("x", 1), List.of(Map.of("oss_url", "u")));

        ArgumentCaptor<String> payloadCaptor = ArgumentCaptor.forClass(String.class);
        verify(listOps).leftPush(anyString(), payloadCaptor.capture());

        JsonNode json = objectMapper.readTree(payloadCaptor.getValue());
        assertThat(json.get("headers").get("task").asText()).isEqualTo("tasks.generate_script_task");

        String body = json.get("body").asText();
        String decoded = new String(Base64.getDecoder().decode(body), StandardCharsets.UTF_8);
        JsonNode bodyJson = objectMapper.readTree(decoded);
        assertThat(bodyJson.get(0).get(0).asText()).isEqualTo(projectId.toString());
        assertThat(bodyJson.get(0).get(1).get("x").asInt()).isEqualTo(1);
    }
}
