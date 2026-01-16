package com.aiscene.admin.repository;

import com.aiscene.admin.entity.Project;
import com.aiscene.admin.entity.ProjectStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.UUID;

/**
 * 项目数据访问接口（用于监控）
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Repository
public interface ProjectRepository extends JpaRepository<Project, UUID> {

    /**
     * 根据状态分页查询项目
     *
     * @param status   项目状态
     * @param pageable 分页参数
     * @return 项目分页
     */
    Page<Project> findByStatus(ProjectStatus status, Pageable pageable);

    /**
     * 根据用户ID分页查询项目
     *
     * @param userId   用户ID
     * @param pageable 分页参数
     * @return 项目分页
     */
    Page<Project> findByUserId(Long userId, Pageable pageable);

    /**
     * 根据状态和用户ID分页查询项目
     *
     * @param status   项目状态
     * @param userId   用户ID
     * @param pageable 分页参数
     * @return 项目分页
     */
    Page<Project> findByStatusAndUserId(ProjectStatus status, Long userId, Pageable pageable);

    /**
     * 统计指定状态的项目数量
     *
     * @param status 项目状态
     * @return 数量
     */
    long countByStatus(ProjectStatus status);

    /**
     * 统计今日创建的项目数量
     *
     * @param startOfDay 今日开始时间
     * @return 数量
     */
    @Query("SELECT COUNT(p) FROM Project p WHERE p.createdAt >= :startOfDay")
    long countTodayCreated(@Param("startOfDay") LocalDateTime startOfDay);

    /**
     * 统计今日完成的项目数量
     *
     * @param startOfDay 今日开始时间
     * @return 数量
     */
    @Query("SELECT COUNT(p) FROM Project p WHERE p.status = 'COMPLETED' AND p.createdAt >= :startOfDay")
    long countTodayCompleted(@Param("startOfDay") LocalDateTime startOfDay);

    /**
     * 统计今日失败的项目数量
     *
     * @param startOfDay 今日开始时间
     * @return 数量
     */
    @Query("SELECT COUNT(p) FROM Project p WHERE p.status = 'FAILED' AND p.errorAt >= :startOfDay")
    long countTodayFailed(@Param("startOfDay") LocalDateTime startOfDay);
}
