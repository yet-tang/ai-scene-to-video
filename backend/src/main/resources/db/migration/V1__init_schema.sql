-- Projects Table
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    user_id BIGINT,
    title VARCHAR(255),
    house_info JSONB,
    status VARCHAR(50),
    script_content TEXT,
    final_video_url VARCHAR(1024),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Assets Table
CREATE TABLE assets (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    oss_url VARCHAR(1024),
    duration DOUBLE PRECISION,
    scene_label VARCHAR(50),
    scene_score DOUBLE PRECISION,
    user_label VARCHAR(50),
    sort_order INTEGER,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- RenderJobs Table
CREATE TABLE render_jobs (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    progress INTEGER,
    error_log TEXT
);
