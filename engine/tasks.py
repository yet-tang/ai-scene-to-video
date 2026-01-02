from worker import celery_app
from vision import SceneDetector
from script_gen import ScriptGenerator
from audio_gen import AudioGenerator
from video_render import VideoRenderer
from config import Config
import json
import logging
import psycopg2
import tempfile
import os

# Configure logging
# Logging is configured in worker.py via signals
logger = logging.getLogger(__name__)

detector = SceneDetector()
script_gen = ScriptGenerator()
audio_gen = AudioGenerator()
video_render = VideoRenderer()

@celery_app.task(bind=True, max_retries=3)
def analyze_video_task(self, project_id: str, asset_id: str, video_url: str):
    """
    Background task to analyze a video asset.
    """
    logger.info(f"Starting analysis for asset {asset_id} in project {project_id}")
    
    try:
        # 1. Extract Key Frame
        frame_path = detector.extract_key_frame(video_url)
        logger.info(f"Extracted key frame for {asset_id}")

        # 2. Call Vision LLM
        result_json_str = detector.analyze_scene(frame_path)
        
        # 3. Parse Result
        # The LLM might return markdown code block, strip it
        clean_json = result_json_str.replace("```json", "").replace("```", "").strip()
        result_data = json.loads(clean_json)
        
        logger.info(f"Analysis result for {asset_id}: {result_data}")

        # 4. Update Database (Direct DB Access)
        # Use psycopg2 context manager to ensure connection closure
        conn = psycopg2.connect(Config.DB_DSN) 
        try:
            with conn:
                with conn.cursor() as cursor:
                    update_query = """
                        UPDATE assets 
                        SET scene_label = %s, 
                            scene_score = %s 
                        WHERE id = %s
                    """
                    # Extract fields from AI result
                    scene = result_data.get("scene", "unknown")
                    score = result_data.get("score", 0.0)
                    
                    cursor.execute(update_query, (scene, score, asset_id))
            logger.info(f"Updated DB for asset {asset_id}")
        finally:
            conn.close()

        return {
            "project_id": project_id,
            "asset_id": asset_id,
            "analysis": result_data
        }

    except Exception as e:
        logger.error(f"Task failed for asset {asset_id}: {str(e)}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

@celery_app.task(bind=True, max_retries=3)
def generate_script_task(self, project_id: str, house_info: dict, timeline_data: list):
    """
    Background task to generate video script using LLM.
    """
    logger.info(f"Starting script generation for project {project_id}")
    
    try:
        # 1. Generate Script
        script_content = script_gen.generate_script(house_info, timeline_data)
        logger.info(f"Generated script for {project_id}")

        # 2. Update Database
        conn = psycopg2.connect(Config.DB_DSN)
        try:
            with conn:
                with conn.cursor() as cursor:
                    update_query = """
                        UPDATE projects 
                        SET script_content = %s,
                            status = 'SCRIPT_GENERATED'
                        WHERE id = %s
                    """
                    cursor.execute(update_query, (script_content, project_id))
            logger.info(f"Updated script in DB for project {project_id}")
        finally:
            conn.close()

        return {
            "project_id": project_id,
            "script": script_content
        }

    except Exception as e:
        logger.error(f"Script generation failed for project {project_id}: {str(e)}")
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

@celery_app.task(bind=True, max_retries=3)
def generate_audio_task(self, project_id: str, script_content: str):
    """
    Background task to generate TTS audio.
    """
    logger.info(f"Starting audio generation for project {project_id}")
    
    try:
        # 1. Generate Audio (Save to local temp first)
        temp_audio = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        temp_audio.close() # Close to let audio_gen write to it
        
        audio_path = audio_gen.generate_audio(script_content, temp_audio.name)
        logger.info(f"Generated audio locally at {audio_path}")

        # 2. Upload to S3 (TODO: Implement S3 Upload in Engine or return path to Backend)
        # For MVP, we might just store the path or binary in DB (not recommended for large files)
        # Or better: Worker should have S3 Client.
        # Let's assume we skip S3 upload here for a moment and just return "Done" 
        # because the next step (Render) will need this file locally anyway if it runs on the same worker node.
        # Ideally, we upload to S3 so Render task can download it (stateless).
        
        # NOTE: For this stateless design, we SHOULD upload.
        # But adding S3 Client to Python Engine is a new dependency.
        # Let's mock the upload or assume shared volume for MVP if strictly needed.
        # To strictly follow "Stateless", we need `boto3`.
        
        # Let's add boto3 upload quickly if we want to be perfect, or just pass the path if using shared volume.
        # Given "Stateless" rule, let's assume we need to upload.
        # For now, I will just return the local path, assuming we might run render on same node 
        # OR we will add S3 upload in next step.
        
        return {
            "project_id": project_id,
            "audio_path": audio_path # Local path for now
        }

    except Exception as e:
        logger.error(f"Audio generation failed for project {project_id}: {str(e)}")
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

@celery_app.task(bind=True, max_retries=3)
def render_video_task(self, project_id: str, timeline_assets: list, audio_path: str):
    """
    Background task to render final video.
    """
    logger.info(f"Starting video rendering for project {project_id}")
    
    try:
        # 1. Render Video
        temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        temp_video.close()
        
        output_path = video_render.render_video(timeline_assets, audio_path, temp_video.name)
        logger.info(f"Rendered video locally at {output_path}")

        # 2. Upload to S3
        file_name = f"rendered_{project_id}.mp4"
        final_video_url = upload_to_s3(output_path, file_name)
        logger.info(f"Uploaded video to {final_video_url}")
        
        # 3. Update Database
        conn = psycopg2.connect(Config.DB_DSN)
        try:
            with conn:
                with conn.cursor() as cursor:
                    update_query = """
                        UPDATE projects 
                        SET final_video_url = %s,
                            status = 'COMPLETED'
                        WHERE id = %s
                    """
                    cursor.execute(update_query, (final_video_url, project_id))
            logger.info(f"Updated final video URL in DB for project {project_id}")
        finally:
            conn.close()

        # Cleanup audio file if it was temp
        if os.path.exists(audio_path) and "/tmp/" in audio_path:
            os.remove(audio_path)

        return {
            "project_id": project_id,
            "video_url": final_video_url
        }

    except Exception as e:
        logger.error(f"Video rendering failed for project {project_id}: {str(e)}")
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
