package com.aiscene.config;

import lombok.Getter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * Built-in Background Music Configuration
 * 
 * Manages a curated list of warm, cozy BGM tracks for real estate videos.
 * BGM files should be uploaded to S3 and their public URLs configured here.
 */
@Component
@ConfigurationProperties(prefix = "app.bgm")
@Getter
public class BgmConfig {
    
    /**
     * List of built-in BGM public URLs.
     * These should be hosted on S3 or CDN for reliable access.
     */
    private List<String> builtinUrls = new ArrayList<>();
    
    /**
     * Whether to auto-select BGM on project creation.
     * Default: true
     */
    private boolean autoSelect = true;
    
    private final Random random = new Random();
    
    /**
     * Get a random BGM URL from the built-in list.
     * Returns null if list is empty.
     */
    public String getRandomBgmUrl() {
        if (builtinUrls == null || builtinUrls.isEmpty()) {
            return null;
        }
        int index = random.nextInt(builtinUrls.size());
        return builtinUrls.get(index);
    }
    
    /**
     * Check if built-in BGM list is available.
     */
    public boolean hasBuiltinBgm() {
        return builtinUrls != null && !builtinUrls.isEmpty();
    }
    
    /**
     * Get total count of built-in BGM tracks.
     */
    public int getBuiltinCount() {
        return builtinUrls == null ? 0 : builtinUrls.size();
    }
    
    public void setBuiltinUrls(List<String> builtinUrls) {
        this.builtinUrls = builtinUrls;
    }
    
    public void setAutoSelect(boolean autoSelect) {
        this.autoSelect = autoSelect;
    }
}
