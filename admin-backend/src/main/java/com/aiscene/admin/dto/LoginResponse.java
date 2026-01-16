package com.aiscene.admin.dto;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 登录响应 DTO
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Data
@Builder
public class LoginResponse {

    private String token;
    private String username;
    private String displayName;
    private String role;
    private LocalDateTime expiresAt;
}
