package com.aiscene.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.UUID;

@Entity
@Table(name = "render_jobs")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RenderJob {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "project_id")
    private Project project;

    private Integer progress;

    @Column(name = "error_log", columnDefinition = "text")
    private String errorLog;
}
