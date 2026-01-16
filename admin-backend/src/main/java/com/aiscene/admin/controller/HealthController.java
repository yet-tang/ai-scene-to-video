package com.aiscene.admin.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 健康检查控制器
 *
 * @author aiscene
 * @since 2026-01-16
 */
@RestController
public class HealthController {

    /**
     * Liveness Probe
     */
    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("OK");
    }

    /**
     * Readiness Probe
     */
    @GetMapping("/ready")
    public ResponseEntity<String> ready() {
        return ResponseEntity.ok("OK");
    }
}
