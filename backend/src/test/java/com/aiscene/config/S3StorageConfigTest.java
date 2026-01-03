package com.aiscene.config;

import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import software.amazon.awssdk.services.s3.S3Client;

import static org.assertj.core.api.Assertions.assertThat;

class S3StorageConfigTest {

    @Test
    void s3Client_buildsClient() {
        S3StorageConfig config = new S3StorageConfig();
        ReflectionTestUtils.setField(config, "region", "us-east-1");
        ReflectionTestUtils.setField(config, "endpoint", "http://localhost:9000");
        ReflectionTestUtils.setField(config, "accessKey", "k");
        ReflectionTestUtils.setField(config, "secretKey", "s");

        S3Client client = config.s3Client();
        assertThat(client).isNotNull();
        client.close();
    }
}

