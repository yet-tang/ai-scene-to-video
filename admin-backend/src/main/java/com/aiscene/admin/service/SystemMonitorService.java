package com.aiscene.admin.service;

import com.aiscene.admin.dto.SystemHealthResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import javax.sql.DataSource;
import java.sql.Connection;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * 系统监控服务
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class SystemMonitorService {

    private final DataSource dataSource;
    private final StringRedisTemplate redisTemplate;
    private final RestTemplate restTemplate = new RestTemplate();

    @Value("${admin.flower.base-url}")
    private String flowerBaseUrl;

    private static final String CELERY_QUEUE_NAME = "ai-video:celery";

    /**
     * 获取系统健康状态
     *
     * @return 系统健康状态
     */
    public SystemHealthResponse getSystemHealth() {
        return SystemHealthResponse.builder()
                .backend(checkBackendHealth())
                .database(checkDatabaseHealth())
                .redis(checkRedisHealth())
                .celery(checkCeleryHealth())
                .build();
    }

    /**
     * 检查 Backend 健康状态
     */
    private SystemHealthResponse.ServiceHealth checkBackendHealth() {
        return SystemHealthResponse.ServiceHealth.builder()
                .name("Admin Backend")
                .status(SystemHealthResponse.ServiceHealth.STATUS_HEALTHY)
                .responseTimeMs(0)
                .message("Service is running")
                .checkedAt(LocalDateTime.now())
                .build();
    }

    /**
     * 检查数据库健康状态
     */
    private SystemHealthResponse.ServiceHealth checkDatabaseHealth() {
        long startTime = System.currentTimeMillis();
        try (Connection conn = dataSource.getConnection()) {
            if (conn.isValid(5)) {
                int responseTime = (int) (System.currentTimeMillis() - startTime);
                return SystemHealthResponse.ServiceHealth.builder()
                        .name("PostgreSQL")
                        .status(SystemHealthResponse.ServiceHealth.STATUS_HEALTHY)
                        .responseTimeMs(responseTime)
                        .message("Connection valid")
                        .checkedAt(LocalDateTime.now())
                        .build();
            }
        } catch (Exception e) {
            log.error("Database health check failed", e);
        }

        int responseTime = (int) (System.currentTimeMillis() - startTime);
        return SystemHealthResponse.ServiceHealth.builder()
                .name("PostgreSQL")
                .status(SystemHealthResponse.ServiceHealth.STATUS_DOWN)
                .responseTimeMs(responseTime)
                .message("Connection failed")
                .checkedAt(LocalDateTime.now())
                .build();
    }

    /**
     * 检查 Redis 健康状态
     */
    private SystemHealthResponse.ServiceHealth checkRedisHealth() {
        long startTime = System.currentTimeMillis();
        try {
            String result = redisTemplate.getConnectionFactory().getConnection().ping();
            if ("PONG".equals(result)) {
                int responseTime = (int) (System.currentTimeMillis() - startTime);
                return SystemHealthResponse.ServiceHealth.builder()
                        .name("Redis")
                        .status(SystemHealthResponse.ServiceHealth.STATUS_HEALTHY)
                        .responseTimeMs(responseTime)
                        .message("PONG")
                        .checkedAt(LocalDateTime.now())
                        .build();
            }
        } catch (Exception e) {
            log.error("Redis health check failed", e);
        }

        int responseTime = (int) (System.currentTimeMillis() - startTime);
        return SystemHealthResponse.ServiceHealth.builder()
                .name("Redis")
                .status(SystemHealthResponse.ServiceHealth.STATUS_DOWN)
                .responseTimeMs(responseTime)
                .message("Connection failed")
                .checkedAt(LocalDateTime.now())
                .build();
    }

    /**
     * 检查 Celery 健康状态
     */
    private SystemHealthResponse.CeleryStatus checkCeleryHealth() {
        // 从 Redis 获取队列长度
        Long pendingTasks = 0L;
        try {
            pendingTasks = redisTemplate.opsForList().size(CELERY_QUEUE_NAME);
        } catch (Exception e) {
            log.warn("Failed to get Celery queue length", e);
        }

        // 尝试从 Flower 获取更多信息
        List<SystemHealthResponse.WorkerInfo> workers = new ArrayList<>();
        int activeTasks = 0;

        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> response = restTemplate.getForObject(
                    flowerBaseUrl + "/api/workers",
                    Map.class
            );

            if (response != null) {
                for (Map.Entry<String, Object> entry : response.entrySet()) {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> workerData = (Map<String, Object>) entry.getValue();

                    @SuppressWarnings("unchecked")
                    Map<String, Object> stats = (Map<String, Object>) workerData.get("stats");
                    int processed = 0;
                    if (stats != null && stats.get("total") != null) {
                        @SuppressWarnings("unchecked")
                        Map<String, Integer> total = (Map<String, Integer>) stats.get("total");
                        processed = total.values().stream().mapToInt(Integer::intValue).sum();
                    }

                    @SuppressWarnings("unchecked")
                    List<Object> active = (List<Object>) workerData.get("active");
                    int workerActiveTasks = active != null ? active.size() : 0;
                    activeTasks += workerActiveTasks;

                    workers.add(SystemHealthResponse.WorkerInfo.builder()
                            .name(entry.getKey())
                            .status("ONLINE")
                            .activeTasks(workerActiveTasks)
                            .processedTasks(processed)
                            .build());
                }
            }
        } catch (Exception e) {
            log.warn("Failed to get Flower workers info: {}", e.getMessage());
        }

        return SystemHealthResponse.CeleryStatus.builder()
                .queueName(CELERY_QUEUE_NAME)
                .pendingTasks(pendingTasks != null ? pendingTasks.intValue() : 0)
                .activeTasks(activeTasks)
                .workers(workers)
                .build();
    }
}
