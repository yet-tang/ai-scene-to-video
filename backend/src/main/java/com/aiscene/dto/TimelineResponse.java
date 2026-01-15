package com.aiscene.dto;

import com.aiscene.entity.Asset;
import com.aiscene.entity.ProjectStatus;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class TimelineResponse {
    private String projectId;
    private String projectTitle;
    private ProjectStatus status;
    private String errorRequestId;
    private String errorStep;
    private List<Asset> assets;
    private JsonNode scriptContent;
}
