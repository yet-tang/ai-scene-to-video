package com.aiscene.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

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
    private String houseInfo;

    @Enumerated(EnumType.STRING)
    private ProjectStatus status;

    @Column(name = "script_content", columnDefinition = "text")
    private String scriptContent;

    @Column(name = "final_video_url")
    private String finalVideoUrl;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
