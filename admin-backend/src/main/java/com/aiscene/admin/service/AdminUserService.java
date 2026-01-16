package com.aiscene.admin.service;

import com.aiscene.admin.dto.AdminUserResponse;
import com.aiscene.admin.dto.CreateAdminUserRequest;
import com.aiscene.admin.entity.AdminUser;
import com.aiscene.admin.repository.AdminUserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

/**
 * 管理员用户服务
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AdminUserService {

    private final AdminUserRepository adminUserRepository;
    private final PasswordEncoder passwordEncoder;

    /**
     * 分页获取管理员列表
     *
     * @param pageable 分页参数
     * @return 管理员分页
     */
    @Transactional(readOnly = true)
    public Page<AdminUserResponse> listUsers(Pageable pageable) {
        return adminUserRepository.findAll(pageable).map(this::toResponse);
    }

    /**
     * 获取管理员详情
     *
     * @param userId 用户ID
     * @return 管理员详情
     */
    @Transactional(readOnly = true)
    public AdminUserResponse getUser(UUID userId) {
        AdminUser user = adminUserRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("用户不存在"));
        return toResponse(user);
    }

    /**
     * 创建管理员
     *
     * @param request 创建请求
     * @return 创建的管理员
     */
    @Transactional
    public AdminUserResponse createUser(CreateAdminUserRequest request) {
        if (adminUserRepository.existsByUsername(request.getUsername())) {
            throw new IllegalArgumentException("用户名已存在");
        }

        AdminUser user = new AdminUser();
        user.setUsername(request.getUsername());
        user.setPasswordHash(passwordEncoder.encode(request.getPassword()));
        user.setDisplayName(request.getDisplayName());
        user.setEmail(request.getEmail());
        user.setRole(request.getRole());
        user.setIsEnabled(true);

        adminUserRepository.save(user);
        log.info("Created admin user: {}", user.getUsername());

        return toResponse(user);
    }

    /**
     * 更新管理员状态（启用/禁用）
     *
     * @param userId    用户ID
     * @param isEnabled 是否启用
     * @return 更新后的管理员
     */
    @Transactional
    public AdminUserResponse updateUserStatus(UUID userId, boolean isEnabled) {
        AdminUser user = adminUserRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("用户不存在"));

        user.setIsEnabled(isEnabled);
        adminUserRepository.save(user);

        log.info("Updated admin user status: {} -> {}", user.getUsername(), isEnabled);
        return toResponse(user);
    }

    /**
     * 删除管理员
     *
     * @param userId 用户ID
     */
    @Transactional
    public void deleteUser(UUID userId) {
        AdminUser user = adminUserRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("用户不存在"));

        // 不允许删除最后一个管理员
        if (user.getRole() == AdminUser.AdminRole.ADMIN) {
            long adminCount = adminUserRepository.findAll().stream()
                    .filter(u -> u.getRole() == AdminUser.AdminRole.ADMIN)
                    .count();
            if (adminCount <= 1) {
                throw new IllegalArgumentException("不能删除最后一个管理员");
            }
        }

        adminUserRepository.delete(user);
        log.info("Deleted admin user: {}", user.getUsername());
    }

    /**
     * 转换为响应 DTO
     */
    private AdminUserResponse toResponse(AdminUser user) {
        return AdminUserResponse.builder()
                .id(user.getId())
                .username(user.getUsername())
                .displayName(user.getDisplayName())
                .email(user.getEmail())
                .role(user.getRole())
                .isEnabled(user.getIsEnabled())
                .lastLoginAt(user.getLastLoginAt())
                .createdAt(user.getCreatedAt())
                .build();
    }
}
