# Implementation Plan: Unified Render Pipeline & Audio Persistence

This plan implements "Plan B" (Unified Pipeline) and "Plan C" (Audio Persistence) to resolve race conditions and ensure statelessness.

## 1. Database & Backend Entity Update
*   **Goal**: Persist the generated audio URL so it's accessible across tasks/workers.
*   **Actions**:
    1.  Create Flyway migration `V2__add_audio_url_to_projects.sql` to add `audio_url` (TEXT) to the `projects` table.
    2.  Update [Project.java](file:///Users/zijun/X-Projects/ai-scene-to-video/backend/src/main/java/com/aiscene/entity/Project.java) to include the `audioUrl` field.

## 2. Engine: Enhanced S3 Upload & Audio Persistence
*   **Goal**: Ensure audio files are uploaded to S3 with correct MIME types and recorded in DB.
*   **Actions**:
    1.  Modify `upload_to_s3` in [tasks.py](file:///Users/zijun/X-Projects/ai-scene-to-video/engine/tasks.py) to accept an optional `content_type` parameter (defaulting to `video/mp4` for backward compatibility, but allowing `audio/mpeg` for MP3s).
    2.  Update `generate_audio_task` in [tasks.py](file:///Users/zijun/X-Projects/ai-scene-to-video/engine/tasks.py) to:
        - Upload the generated MP3 to S3.
        - Update the `projects` table with `audio_url`.

## 3. Engine: Unified Render Pipeline Task
*   **Goal**: Create a single atomic task that guarantees "Audio First, then Render" sequence.
*   **Actions**:
    1.  Implement a new Celery task `render_pipeline_task` in [tasks.py](file:///Users/zijun/X-Projects/ai-scene-to-video/engine/tasks.py).
    2.  **Logic Flow**:
        - **Step 1 (Audio)**: Generate audio locally -> Upload to S3 -> Update DB (`audio_url`, status=`AUDIO_GENERATED`).
        - **Step 2 (Render)**: Use the local audio file (since we are in the same task/container, we can skip downloading) to render the video.
        - **Step 3 (Finalize)**: Upload video to S3 -> Update DB (`final_video_url`, status=`COMPLETED`).
    3.  This task will accept `project_id`, `script_content`, and `timeline_assets` as arguments.

## 4. Backend: Trigger the Pipeline
*   **Goal**: Switch the "Render" button logic to use the new pipeline.
*   **Actions**:
    1.  Update [TaskQueueService.java](file:///Users/zijun/X-Projects/ai-scene-to-video/backend/src/main/java/com/aiscene/service/TaskQueueService.java) to add `submitRenderPipelineTask`.
    2.  Update [ProjectService.java](file:///Users/zijun/X-Projects/ai-scene-to-video/backend/src/main/java/com/aiscene/service/ProjectService.java) in `renderVideo` method:
        - Instead of assuming audio exists and triggering `render_video_task`, it will now collect the script content and assets, then trigger `render_pipeline_task`.

## 5. Verification
*   **Validation**:
    - Verify `audio_url` appears in the `projects` table after audio generation.
    - Verify `render_pipeline_task` executes successfully without `audio not ready` errors.
    - Verify S3 contains both audio and video artifacts.
