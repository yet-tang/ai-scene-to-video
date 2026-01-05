package com.aiscene.entity;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.ColumnTransformer;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "projects")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Project {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "user_id")
    private Long userId;

    private String title;

    // Storing JSON as String for simplicity in MVP. 
    // In production, consider using a proper JSON Type with Hypersistence Utils.
    @Column(name = "house_info", columnDefinition = "jsonb")
    @JdbcTypeCode(SqlTypes.JSON)
    @ColumnTransformer(write = "?::jsonb")
    private JsonNode houseInfo;

    @Enumerated(EnumType.STRING)
    private ProjectStatus status;

    @Column(name = "script_content", columnDefinition = "text")
    private String scriptContent;

    @Column(name = "audio_url")
    private String audioUrl;

    @Column(name = "final_video_url")
    private String finalVideoUrl;

    @Column(name = "error_log", columnDefinition = "text")
    private String errorLog;

    @Column(name = "error_task_id")
    private String errorTaskId;

    @Column(name = "error_request_id")
    private String errorRequestId;

    @Column(name = "error_step")
    private String errorStep;

    @Column(name = "error_at")
    private LocalDateTime errorAt;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
