from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
import os
import tempfile
import cv2

class VideoRenderer:
    def __init__(self):
        pass

    def render_video(self, timeline_assets: list, audio_path: str, output_path: str) -> str:
        """
        Concatenate video clips based on timeline and add audio track.
        """
        video_clips = []
        
        # 1. Process Video Clips
        for asset in timeline_assets:
            url = asset.get('oss_url')
            # For MVP, we need to download video from URL to local temp
            # Using OpenCV to check if we can stream, but MoviePy usually needs a file.
            # Let's download to temp.
            local_video_path = self._download_temp(url)
            
            clip = VideoFileClip(local_video_path)
            
            # Basic resize to standard 1080x1920 (Vertical) or 1920x1080 (Horizontal)
            # Assuming vertical for Shorts/TikTok
            # clip = clip.resize(height=1920) 
            # clip = clip.crop(x1=..., width=1080) # Center crop logic TODO
            # For MVP: Just resize to height 720 to keep it fast and simple
            clip = clip.resize(height=720)
            
            video_clips.append(clip)

        if not video_clips:
            raise ValueError("No video clips to render")

        # 2. Concatenate Clips
        final_video = concatenate_videoclips(video_clips, method="compose")

        # 3. Add Audio
        if audio_path and os.path.exists(audio_path):
            audio_clip = AudioFileClip(audio_path)
            
            # Loop video or cut audio?
            # Strategy: Audio drives the length.
            # If video is shorter than audio, loop video (complex) or just black screen?
            # Or make video clips longer?
            # MVP Strategy: If audio is longer, cut audio. If video is longer, cut video.
            # Actually, standard is: Video matches Audio.
            
            # Simple MVP: Set final video duration to match audio
            final_duration = audio_clip.duration
            if final_video.duration > final_duration:
                final_video = final_video.subclip(0, final_duration)
            else:
                # Video too short, maybe slow down or loop?
                # For now, just keep it short (audio will cut off? or video black?)
                # MoviePy set_audio will handle it, but video stops.
                pass
            
            final_video = final_video.set_audio(audio_clip)

        # 4. Write Output
        final_video.write_videofile(output_path, codec='libx264', audio_codec='aac', fps=24)
        
        # Cleanup clips to release resources
        for clip in video_clips:
            clip.close()
            # Remove temp files
            if os.path.exists(clip.filename):
                os.remove(clip.filename)
                
        return output_path

    def _download_temp(self, url: str) -> str:
        # Re-using OpenCV or just requests to download
        # Since we have OpenCV in vision.py, let's use requests (need to add to requirements if not there)
        # Actually we don't have requests in requirements explicitly but dashscope might pull it.
        # Let's use urllib for zero dependency
        import urllib.request
        
        temp = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        temp.close()
        urllib.request.urlretrieve(url, temp.name)
        return temp.name
