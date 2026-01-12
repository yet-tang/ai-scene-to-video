package com.aiscene;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;

@SpringBootApplication
public class AiSceneApplication {

    private static final Logger logger = LoggerFactory.getLogger(AiSceneApplication.class);

    public static void main(String[] args) {
        SpringApplication.run(AiSceneApplication.class, args);
    }

    @EventListener(ApplicationReadyEvent.class)
    public void onApplicationReady() {
        String imageTag = System.getProperty("image.tag", "unknown");
        String gitCommit = System.getProperty("git.commit", "unknown");
        String buildTime = System.getProperty("build.time", "unknown");
        
        logger.info("=== Backend Version Info ===");
        logger.info("Image Tag: {}", imageTag);
        logger.info("Git Commit: {}", gitCommit);
        logger.info("Build Time: {}", buildTime);
        logger.info("============================");
    }

}
