-- Change script_content to JSONB, handling existing plain text by converting it to JSON strings
ALTER TABLE projects ALTER COLUMN script_content TYPE JSONB 
USING (
    CASE 
        WHEN script_content IS NULL THEN NULL
        WHEN script_content IS JSON THEN script_content::jsonb 
        ELSE to_jsonb(script_content) 
    END
);
