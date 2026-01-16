package com.aiscene.admin.repository;

import com.aiscene.admin.entity.AiModel;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

/**
 * AI 模型配置数据访问接口
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Repository
public interface AiModelRepository extends JpaRepository<AiModel, UUID> {

    /**
     * 查找所有启用的模型
     *
     * @return 启用的模型列表
     */
    List<AiModel> findByIsEnabledTrue();

    /**
     * 根据提供商查找模型
     *
     * @param provider 提供商名称
     * @return 模型列表
     */
    List<AiModel> findByProvider(String provider);

    /**
     * 根据 Agent 类型查找模型
     *
     * @param agentType Agent 类型
     * @return 模型列表
     */
    List<AiModel> findByAgentType(String agentType);
}
