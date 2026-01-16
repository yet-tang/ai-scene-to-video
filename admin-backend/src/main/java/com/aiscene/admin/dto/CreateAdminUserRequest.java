package com.aiscene.admin.dto;

import com.aiscene.admin.entity.AdminUser;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 创建管理员请求 DTO
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Data
public class CreateAdminUserRequest {

    @NotBlank(message = "用户名不能为空")
    @Size(min = 3, max = 50, message = "用户名长度必须在3-50个字符之间")
    private String username;

    @NotBlank(message = "密码不能为空")
    @Size(min = 6, max = 100, message = "密码长度必须在6-100个字符之间")
    private String password;

    @Size(max = 100, message = "显示名称不能超过100个字符")
    private String displayName;

    @Size(max = 100, message = "邮箱不能超过100个字符")
    private String email;

    private AdminUser.AdminRole role = AdminUser.AdminRole.VIEWER;
}
