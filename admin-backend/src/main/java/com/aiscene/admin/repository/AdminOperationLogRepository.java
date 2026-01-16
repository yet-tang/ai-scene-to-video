package com.aiscene.admin.repository;

import com.aiscene.admin.entity.AdminOperationLog;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.UUID;

/**
 * 管理员操作日志数据访问接口
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Repository
public interface AdminOperationLogRepository extends JpaRepository<AdminOperationLog, UUID> {

    /**
     * 根据管理员ID分页查询操作日志
     *
     * @param adminUserId 管理员ID
     * @param pageable    分页参数
     * @return 操作日志分页
     */
    Page<AdminOperationLog> findByAdminUserId(UUID adminUserId, Pageable pageable);

    /**
     * 根据操作类型分页查询
     *
     * @param operation 操作类型
     * @param pageable  分页参数
     * @return 操作日志分页
     */
    Page<AdminOperationLog> findByOperation(String operation, Pageable pageable);
}
