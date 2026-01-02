package com.aiscene.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;

import java.net.URI;

@Configuration
public class S3StorageConfig {

    @Value("${s3.storage.region}")
    private String region;

    @Value("${s3.storage.endpoint}")
    private String endpoint;

    @Value("${s3.storage.access-key}")
    private String accessKey;

    @Value("${s3.storage.secret-key}")
    private String secretKey;

    @Bean
    public S3Client s3Client() {
        // For Cloudflare R2, we must specify a region (usually 'auto' or 'us-east-1')
        // even though R2 is global. The SDK requires it.
        // Also R2 supports path-style access (e.g. https://<account>.r2.cloudflarestorage.com/<bucket>)
        return S3Client.builder()
                .region(Region.of(region)) 
                .endpointOverride(URI.create(endpoint))
                .credentialsProvider(StaticCredentialsProvider.create(
                        AwsBasicCredentials.create(accessKey, secretKey)
                ))
                .forcePathStyle(true) 
                .build();
    }
}
