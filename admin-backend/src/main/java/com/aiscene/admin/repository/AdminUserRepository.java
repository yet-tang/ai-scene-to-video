package com.aiscene.admin.repository;

import com.aiscene.admin.entity.AdminUser;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

/**
 * 管理员用户数据访问接口
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Repository
public interface AdminUserRepository extends JpaRepository<AdminUser, UUID> {

    /**
     * 根据用户名查找管理员
     *
     * @param username 用户名
     * @return 管理员用户
     */
    Optional<AdminUser> findByUsername(String username);

    /**
     * 检查用户名是否存在
     *
     * @param username 用户名
     * @return true 如果存在
     */
    boolean existsByUsername(String username);
}
