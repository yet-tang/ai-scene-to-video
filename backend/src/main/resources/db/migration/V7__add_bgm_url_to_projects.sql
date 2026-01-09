-- Add bgm_url field to projects table for built-in BGM support
ALTER TABLE projects ADD COLUMN IF NOT EXISTS bgm_url TEXT;

-- Add comment for documentation
COMMENT ON COLUMN projects.bgm_url IS 'URL of background music (auto-selected from built-in list or user-uploaded)';
