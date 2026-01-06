package com.aiscene.service;

import com.aiscene.dto.PresignedUrlResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;
import software.amazon.awssdk.services.s3.presigner.model.PutObjectPresignRequest;

import java.io.InputStream;
import java.net.URI;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class StorageService {

    private final S3Client s3Client;
    private final S3Presigner s3Presigner;

    @Value("${s3.storage.bucket}")
    private String bucketName;

    @Value("${s3.storage.public-url}")
    private String publicUrlBase;

    public String getBucketName() {
        return bucketName;
    }

    public record UploadedObject(String objectKey, String publicUrl) {}

    public PresignedUrlResponse generatePresignedUrl(String objectKey, String contentType) {
        try {
            PutObjectRequest objectRequest = PutObjectRequest.builder()
                    .bucket(bucketName)
                    .key(objectKey)
                    .contentType(contentType)
                    .build();

            PutObjectPresignRequest presignRequest = PutObjectPresignRequest.builder()
                    .signatureDuration(Duration.ofMinutes(20))
                    .putObjectRequest(objectRequest)
                    .build();

            var presignedRequest = s3Presigner.presignPutObject(presignRequest);

            String uploadUrl = presignedRequest.url().toString();
            String publicUrl = getPublicUrl(objectKey);

            Map<String, String> headers = new HashMap<>();
            headers.put("Content-Type", contentType);

            return PresignedUrlResponse.builder()
                    .uploadUrl(uploadUrl)
                    .publicUrl(publicUrl)
                    .objectKey(objectKey)
                    .signedHeaders(headers)
                    .build();

        } catch (Exception e) {
            log.error("Error generating presigned URL", e);
            throw new RuntimeException("Failed to generate presigned URL", e);
        }
    }

    public String getPublicUrl(String objectKey) {
        String base = publicUrlBase;
        if (base.endsWith("/")) {
            base = base.substring(0, base.length() - 1);
        }
        if (!base.startsWith("http://") && !base.startsWith("https://")) {
            base = "https://" + base;
        }

        URI uri = URI.create(base);
        String host = uri.getHost();
        String path = uri.getPath();

        if (path != null && (path.equals("/" + bucketName) || path.startsWith("/" + bucketName + "/"))) {
            return base + "/" + objectKey;
        }

        if (host != null && host.startsWith(bucketName + ".")) {
            return base + "/" + objectKey;
        }

        if (host != null && (host.contains(".r2.cloudflarestorage.com") || host.contains(".amazonaws.com") || host.contains("localhost"))) {
            return base + "/" + bucketName + "/" + objectKey;
        }

        return base + "/" + objectKey;
    }

    public String uploadFile(MultipartFile file) {
        try {
            // Note: The bucket must be created beforehand.
            // We skip bucket creation logic here to keep permissions simple.

            UploadedObject uploaded = uploadFileAndReturnObject(file);
            return uploaded.publicUrl();

        } catch (Exception e) {
            log.error("Error uploading file to S3 Storage", e);
            throw new RuntimeException("Failed to upload file", e);
        }
    }

    public UploadedObject uploadFileAndReturnObject(MultipartFile file) {
        try {
            String objectKey = UUID.randomUUID() + "-" + file.getOriginalFilename();
            InputStream inputStream = file.getInputStream();

            PutObjectRequest putObjectRequest = PutObjectRequest.builder()
                    .bucket(bucketName)
                    .key(objectKey)
                    .contentType(file.getContentType())
                    .build();

            s3Client.putObject(
                    putObjectRequest,
                    RequestBody.fromInputStream(inputStream, file.getSize())
            );

            return new UploadedObject(objectKey, getPublicUrl(objectKey));
        } catch (Exception e) {
            log.error("Error uploading file to S3 Storage", e);
            throw new RuntimeException("Failed to upload file", e);
        }
    }
}
