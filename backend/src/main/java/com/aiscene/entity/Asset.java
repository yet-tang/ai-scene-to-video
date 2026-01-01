package com.aiscene.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.UUID;

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
