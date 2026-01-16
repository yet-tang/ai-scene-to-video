package com.aiscene.admin.service;

import com.aiscene.admin.config.JwtUtils;
import com.aiscene.admin.dto.LoginRequest;
import com.aiscene.admin.dto.LoginResponse;
import com.aiscene.admin.entity.AdminOperationLog;
import com.aiscene.admin.entity.AdminUser;
import com.aiscene.admin.repository.AdminOperationLogRepository;
import com.aiscene.admin.repository.AdminUserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.Date;

/**
 * 认证服务
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AuthService {

    private final AdminUserRepository adminUserRepository;
    private final AdminOperationLogRepository operationLogRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtils jwtUtils;

    /**
     * 管理员登录
     *
     * @param request   登录请求
     * @param ipAddress 客户端IP
     * @param userAgent 客户端 User-Agent
     * @return 登录响应
     */
    @Transactional
    public LoginResponse login(LoginRequest request, String ipAddress, String userAgent) {
        AdminUser user = adminUserRepository.findByUsername(request.getUsername())
                .orElseThrow(() -> new IllegalArgumentException("用户名或密码错误"));

        if (!user.getIsEnabled()) {
            logOperation(user, AdminOperationLog.OP_LOGIN, null, null, ipAddress, userAgent,
                    AdminOperationLog.STATUS_FAILED, "账号已禁用");
            throw new IllegalArgumentException("账号已禁用");
        }

        if (!passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            logOperation(user, AdminOperationLog.OP_LOGIN, null, null, ipAddress, userAgent,
                    AdminOperationLog.STATUS_FAILED, "密码错误");
            throw new IllegalArgumentException("用户名或密码错误");
        }

        // 更新最后登录时间
        user.setLastLoginAt(LocalDateTime.now());
        adminUserRepository.save(user);

        // 生成 Token
        String token = jwtUtils.generateToken(user.getId(), user.getUsername(), user.getRole().name());
        Date expirationDate = jwtUtils.getExpirationFromToken(token);
        LocalDateTime expiresAt = Instant.ofEpochMilli(expirationDate.getTime())
                .atZone(ZoneId.systemDefault())
                .toLocalDateTime();

        // 记录登录日志
        logOperation(user, AdminOperationLog.OP_LOGIN, null, null, ipAddress, userAgent,
                AdminOperationLog.STATUS_SUCCESS, null);

        log.info("Admin user logged in: {}", user.getUsername());

        return LoginResponse.builder()
                .token(token)
                .username(user.getUsername())
                .displayName(user.getDisplayName())
                .role(user.getRole().name())
                .expiresAt(expiresAt)
                .build();
    }

    /**
     * 记录操作日志
     */
    public void logOperation(AdminUser user, String operation, String resourceType, String resourceId,
                             String ipAddress, String userAgent, String status, String errorMessage) {
        AdminOperationLog logEntry = new AdminOperationLog();
        logEntry.setAdminUser(user);
        logEntry.setOperation(operation);
        logEntry.setResourceType(resourceType);
        logEntry.setResourceId(resourceId);
        logEntry.setIpAddress(ipAddress);
        logEntry.setUserAgent(userAgent);
        logEntry.setStatus(status);
        logEntry.setErrorMessage(errorMessage);
        operationLogRepository.save(logEntry);
    }
}
