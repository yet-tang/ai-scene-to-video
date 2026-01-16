package com.aiscene.admin.controller;

import com.aiscene.admin.dto.SystemHealthResponse;
import com.aiscene.admin.service.SystemMonitorService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 系统监控控制器
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Slf4j
@RestController
@RequestMapping("/admin/system")
@RequiredArgsConstructor
public class SystemMonitorController {

    private final SystemMonitorService systemMonitorService;

    /**
     * 获取系统健康状态
     *
     * @return 系统健康状态
     */
    @GetMapping("/health")
    public ResponseEntity<SystemHealthResponse> getSystemHealth() {
        SystemHealthResponse health = systemMonitorService.getSystemHealth();
        return ResponseEntity.ok(health);
    }
}
