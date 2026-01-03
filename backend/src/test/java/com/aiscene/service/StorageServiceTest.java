package com.aiscene.service;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.util.ReflectionTestUtils;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

class StorageServiceTest {

    @Test
    void uploadFile_normalizesPublicUrlAndReturnsUrl() {
        S3Client s3Client = mock(S3Client.class);
        S3Presigner s3Presigner = mock(S3Presigner.class);
        StorageService service = new StorageService(s3Client, s3Presigner);
        ReflectionTestUtils.setField(service, "bucketName", "b");
        ReflectionTestUtils.setField(service, "publicUrlBase", "example.com/");

        MockMultipartFile file = new MockMultipartFile("file", "a.txt", "text/plain", "x".getBytes());

        String url = service.uploadFile(file);

        assertThat(url).startsWith("https://example.com/b/");
        verify(s3Client).putObject(any(PutObjectRequest.class), any(RequestBody.class));
    }

    @Test
    void uploadFile_keepsHttpScheme() {
        S3Client s3Client = mock(S3Client.class);
        S3Presigner s3Presigner = mock(S3Presigner.class);
        StorageService service = new StorageService(s3Client, s3Presigner);
        ReflectionTestUtils.setField(service, "bucketName", "b");
        ReflectionTestUtils.setField(service, "publicUrlBase", "http://localhost:9000");

        MockMultipartFile file = new MockMultipartFile("file", "a.txt", "text/plain", "x".getBytes());

        String url = service.uploadFile(file);

        assertThat(url).startsWith("http://localhost:9000/b/");
    }

    @Test
    void uploadFile_throwsOnS3Failure() {
        S3Client s3Client = mock(S3Client.class);
        S3Presigner s3Presigner = mock(S3Presigner.class);
        doThrow(new RuntimeException("fail")).when(s3Client).putObject(any(PutObjectRequest.class), any(RequestBody.class));

        StorageService service = new StorageService(s3Client, s3Presigner);
        ReflectionTestUtils.setField(service, "bucketName", "b");
        ReflectionTestUtils.setField(service, "publicUrlBase", "example.com");

        MockMultipartFile file = new MockMultipartFile("file", "a.txt", "text/plain", "x".getBytes());

        assertThatThrownBy(() -> service.uploadFile(file))
                .isInstanceOf(RuntimeException.class)
                .hasMessageContaining("Failed to upload file");
    }
}

