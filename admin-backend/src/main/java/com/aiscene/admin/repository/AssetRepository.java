package com.aiscene.admin.repository;

import com.aiscene.admin.entity.Asset;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

/**
 * 素材数据访问接口（用于监控）
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Repository
public interface AssetRepository extends JpaRepository<Asset, UUID> {

    /**
     * 根据项目ID查找素材列表
     *
     * @param projectId 项目ID
     * @return 素材列表
     */
    @Query("SELECT a FROM Asset a WHERE a.project.id = :projectId AND a.isDeleted = false ORDER BY a.sortOrder")
    List<Asset> findByProjectIdOrderBySortOrder(@Param("projectId") UUID projectId);

    /**
     * 统计项目的素材数量
     *
     * @param projectId 项目ID
     * @return 数量
     */
    @Query("SELECT COUNT(a) FROM Asset a WHERE a.project.id = :projectId AND a.isDeleted = false")
    long countByProjectId(@Param("projectId") UUID projectId);
}
