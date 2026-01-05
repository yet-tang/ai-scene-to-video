ALTER TABLE projects ADD COLUMN error_log TEXT;
ALTER TABLE projects ADD COLUMN error_task_id VARCHAR(128);
ALTER TABLE projects ADD COLUMN error_request_id VARCHAR(128);
ALTER TABLE projects ADD COLUMN error_step VARCHAR(64);
ALTER TABLE projects ADD COLUMN error_at TIMESTAMP;
