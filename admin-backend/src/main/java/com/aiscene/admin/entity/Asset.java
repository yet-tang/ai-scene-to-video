package com.aiscene.admin.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.UUID;

/**
 * 素材实体（只读，用于监控）
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Entity
@Table(name = "assets")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Asset {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "project_id")
    private Project project;

    @Column(name = "oss_url")
    private String ossUrl;

    @Column(name = "storage_type")
    @Builder.Default
    private String storageType = "S3";

    @Column(name = "storage_bucket")
    private String storageBucket;

    @Column(name = "storage_key")
    private String storageKey;

    @Column(name = "local_path")
    private String localPath;

    private Double duration;

    @Column(name = "scene_label")
    private String sceneLabel;

    @Column(name = "scene_score")
    private Double sceneScore;

    @Column(name = "user_label")
    private String userLabel;

    @Column(name = "sort_order")
    private Integer sortOrder;

    @Column(name = "is_deleted")
    @Builder.Default
    private Boolean isDeleted = false;
}
