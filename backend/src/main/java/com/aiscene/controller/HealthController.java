package com.aiscene.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.sql.DataSource;
import java.sql.Connection;

@RestController
@RequiredArgsConstructor
public class HealthController {

    private final DataSource dataSource;

    // Liveness Probe (Is the process running?)
    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("OK");
    }

    // Readiness Probe (Can we serve traffic?)
    @GetMapping("/ready")
    public ResponseEntity<String> ready() {
        try (Connection conn = dataSource.getConnection()) {
            if (conn.isValid(1)) {
                return ResponseEntity.ok("OK");
            }
        } catch (Exception e) {
            // Log error
        }
        return ResponseEntity.status(503).body("Service Unavailable: DB Connection Failed");
    }
}
