package com.aiscene.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;

import java.io.InputStream;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class StorageService {

    private final S3Client s3Client;

    @Value("${supabase.storage.bucket}")
    private String bucketName;

    @Value("${supabase.storage.public-url}")
    private String publicUrlBase;

    public String uploadFile(MultipartFile file) {
        try {
            // Note: For Supabase, the bucket must be created in the dashboard beforehand.
            // We skip bucket creation logic here to keep permissions simple.

            String fileName = UUID.randomUUID() + "-" + file.getOriginalFilename();
            InputStream inputStream = file.getInputStream();

            PutObjectRequest putObjectRequest = PutObjectRequest.builder()
                    .bucket(bucketName)
                    .key(fileName)
                    .contentType(file.getContentType())
                    .build();

            s3Client.putObject(putObjectRequest, 
                    RequestBody.fromInputStream(inputStream, file.getSize()));

            // Return the Public URL
            return publicUrlBase + "/" + bucketName + "/" + fileName;

        } catch (Exception e) {
            log.error("Error uploading file to Supabase Storage", e);
            throw new RuntimeException("Failed to upload file", e);
        }
    }
}
