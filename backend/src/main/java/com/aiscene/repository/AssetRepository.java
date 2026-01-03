package com.aiscene.repository;

import com.aiscene.entity.Asset;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface AssetRepository extends JpaRepository<Asset, UUID> {
    List<Asset> findByProjectIdOrderBySortOrderAsc(UUID projectId);
    List<Asset> findByProjectIdAndIsDeletedFalseOrderBySortOrderAsc(UUID projectId);
}
