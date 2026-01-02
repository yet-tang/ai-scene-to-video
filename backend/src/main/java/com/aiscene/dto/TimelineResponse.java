package com.aiscene.dto;

import com.aiscene.entity.Asset;
import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class TimelineResponse {
    private String projectId;
    private String projectTitle;
    private List<Asset> assets;
    private String scriptContent;
}
