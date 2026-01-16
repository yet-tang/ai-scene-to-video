package com.aiscene.admin.dto;

import com.aiscene.admin.entity.AdminUser;
import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.UUID;

/**
 * 管理员用户响应 DTO
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Data
@Builder
public class AdminUserResponse {

    private UUID id;
    private String username;
    private String displayName;
    private String email;
    private AdminUser.AdminRole role;
    private Boolean isEnabled;
    private LocalDateTime lastLoginAt;
    private LocalDateTime createdAt;
}
