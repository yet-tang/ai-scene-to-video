package com.aiscene.admin.controller;

import com.aiscene.admin.dto.AdminUserResponse;
import com.aiscene.admin.dto.CreateAdminUserRequest;
import com.aiscene.admin.service.AdminUserService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;
import java.util.UUID;

/**
 * 管理员用户控制器
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Slf4j
@RestController
@RequestMapping("/admin/users")
@RequiredArgsConstructor
public class AdminUserController {

    private final AdminUserService adminUserService;

    /**
     * 分页获取管理员列表
     *
     * @param page 页码
     * @param size 每页大小
     * @return 管理员分页
     */
    @GetMapping
    public ResponseEntity<Page<AdminUserResponse>> listUsers(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {

        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<AdminUserResponse> users = adminUserService.listUsers(pageable);
        return ResponseEntity.ok(users);
    }

    /**
     * 获取管理员详情
     *
     * @param id 用户ID
     * @return 管理员详情
     */
    @GetMapping("/{id}")
    public ResponseEntity<AdminUserResponse> getUser(@PathVariable UUID id) {
        AdminUserResponse user = adminUserService.getUser(id);
        return ResponseEntity.ok(user);
    }

    /**
     * 创建管理员
     *
     * @param request 创建请求
     * @return 创建的管理员
     */
    @PostMapping
    public ResponseEntity<AdminUserResponse> createUser(@Valid @RequestBody CreateAdminUserRequest request) {
        AdminUserResponse user = adminUserService.createUser(request);
        return ResponseEntity.ok(user);
    }

    /**
     * 更新管理员状态
     *
     * @param id      用户ID
     * @param request 包含 isEnabled 字段
     * @return 更新后的管理员
     */
    @PutMapping("/{id}/status")
    public ResponseEntity<AdminUserResponse> updateUserStatus(
            @PathVariable UUID id,
            @RequestBody Map<String, Boolean> request) {

        Boolean isEnabled = request.get("isEnabled");
        if (isEnabled == null) {
            throw new IllegalArgumentException("isEnabled 字段必填");
        }

        AdminUserResponse user = adminUserService.updateUserStatus(id, isEnabled);
        return ResponseEntity.ok(user);
    }

    /**
     * 删除管理员
     *
     * @param id 用户ID
     * @return 空响应
     */
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteUser(@PathVariable UUID id) {
        adminUserService.deleteUser(id);
        return ResponseEntity.noContent().build();
    }
}
