package com.aiscene.dto;

import lombok.Builder;
import lombok.Data;
import java.util.Map;

@Data
@Builder
public class PresignedUrlResponse {
    private String uploadUrl;
    private String publicUrl;
    private String objectKey;
    private Map<String, String> signedHeaders;
}
