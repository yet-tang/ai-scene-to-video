package com.aiscene.dto;

import lombok.Data;
import java.util.UUID;

@Data
public class AssetConfirmRequest {
    private String objectKey;
    private String filename;
    private String contentType;
    private Long size;
}
