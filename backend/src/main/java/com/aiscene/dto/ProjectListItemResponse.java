package com.aiscene.dto;

import com.aiscene.entity.ProjectStatus;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ProjectListItemResponse {
    private UUID id;
    private String title;
    private ProjectStatus status;
    private JsonNode houseInfo;
    private LocalDateTime createdAt;
}
