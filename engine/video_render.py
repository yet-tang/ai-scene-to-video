from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, vfx
import os
import tempfile
import urllib.request

class VideoRenderer:
    def __init__(self):
        pass

    def render_video(self, timeline_assets: list, audio_map: dict, output_path: str) -> str:
        """
        Concatenate video clips based on timeline and add audio track.
        audio_map: dict { asset_id: local_audio_path }
        """
        final_clips = []
        temp_files_to_clean = []
        
        try:
            # 1. Process each asset
            for asset in timeline_assets:
                url = asset.get('oss_url')
                asset_id = asset.get('id')
                
                if not url: 
                    continue
                    
                # Download Video
                local_video_path = self._download_temp(url)
                temp_files_to_clean.append(local_video_path)
                
                try:
                    clip = VideoFileClip(local_video_path)
                except Exception:
                    # Skip corrupt files
                    continue
                    
                # Basic resize to 720p height
                # Note: If mixed aspect ratios, this might be weird. 
                # Assuming all are vertical or we just fit height.
                if clip.h != 720:
                    clip = clip.resize(height=720)
                
                # Get Audio
                audio_path = audio_map.get(asset_id) if audio_map else None
                
                if audio_path and os.path.exists(audio_path):
                    audio_clip = AudioFileClip(audio_path)
                    
                    # 3. Sync Logic (Elastic)
                    # Audio is the Master.
                    audio_dur = audio_clip.duration
                    video_dur = clip.duration
                    
                    # Elastic Match
                    if video_dur >= audio_dur:
                        # Video is longer -> Cut video
                        clip = clip.subclip(0, audio_dur)
                    else:
                        # Video is shorter -> Boomerang Extend
                        # Create a boomerang effect: Forward -> Backward -> Forward ...
                        extended_clips = [clip]
                        current_len = video_dur
                        direction = -1 # Next is backward
                        
                        # Limit loop to reasonable amount (e.g. max 30s)
                        while current_len < audio_dur and current_len < 60:
                            if direction == -1:
                                # Reverse
                                next_part = clip.fx(vfx.time_mirror)
                            else:
                                next_part = clip
                            
                            extended_clips.append(next_part)
                            current_len += video_dur
                            direction *= -1
                        
                        # Concatenate loop parts
                        if len(extended_clips) > 1:
                            full_extended = concatenate_videoclips(extended_clips)
                        else:
                            full_extended = clip
                            
                        # Trim to exact audio length
                        if full_extended.duration > audio_dur:
                            clip = full_extended.subclip(0, audio_dur)
                        else:
                            clip = full_extended
                    
                    # Attach Audio
                    clip = clip.set_audio(audio_clip)
                else:
                    # No audio for this clip? 
                    # Keep original video duration or silence?
                    # Let's keep original video but without audio?
                    # Or maybe skip?
                    # Better to keep it to avoid missing visuals.
                    pass
                
                final_clips.append(clip)

            if not final_clips:
                raise ValueError("No video clips to render")

            # 4. Concatenate All
            final_video = concatenate_videoclips(final_clips, method="compose")

            # 5. Write Output
            final_video.write_videofile(
                output_path, 
                codec='libx264', 
                audio_codec='aac', 
                fps=24,
                preset='veryfast',
                threads=4,
                logger=None 
            )
            
        finally:
            # Cleanup clips
            for clip in final_clips:
                try:
                    clip.close()
                    if clip.audio: clip.audio.close()
                except: pass
            
            # Cleanup temp files
            for p in temp_files_to_clean:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except: pass
                
        return output_path

    def _download_temp(self, url: str) -> str:
        import urllib.request
        if url.startswith("file://"):
            return url.replace("file://", "")
            
        temp = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        temp.close()
        try:
            urllib.request.urlretrieve(url, temp.name)
        except Exception:
            if os.path.exists(temp.name):
                os.remove(temp.name)
            raise
        return temp.name
