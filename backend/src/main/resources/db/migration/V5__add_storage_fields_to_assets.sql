ALTER TABLE assets
    ADD COLUMN storage_type VARCHAR(32) NOT NULL DEFAULT 'S3',
    ADD COLUMN storage_bucket VARCHAR(255),
    ADD COLUMN storage_key VARCHAR(1024),
    ADD COLUMN local_path VARCHAR(1024);
