-- Add description field to projects table for intelligent AI enhancement
ALTER TABLE projects ADD COLUMN IF NOT EXISTS description TEXT;

-- Add comment for documentation
COMMENT ON COLUMN projects.description IS 'House description for AI visual enhancement prompt generation';
