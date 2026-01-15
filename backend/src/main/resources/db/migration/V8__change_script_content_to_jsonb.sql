-- Change script_content to JSONB
ALTER TABLE projects ALTER COLUMN script_content TYPE JSONB USING script_content::jsonb;
