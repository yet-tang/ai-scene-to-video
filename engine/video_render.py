from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, vfx, ColorClip
from config import Config
import boto3
import json
import logging
import os
import subprocess
import tempfile
import time
import urllib.request
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class VideoRenderer:
    def __init__(self):
        self._s3_client = boto3.client(
            "s3",
            endpoint_url=Config.S3_STORAGE_ENDPOINT,
            aws_access_key_id=Config.S3_STORAGE_ACCESS_KEY,
            aws_secret_access_key=Config.S3_STORAGE_SECRET_KEY,
            region_name=Config.S3_STORAGE_REGION,
        )

    def _url_host(self, url: str) -> str:
        try:
            return urlparse(url).hostname or ""
        except Exception:
            return ""

    def _parse_object_key_from_public_url(self, url: str) -> str | None:
        try:
            bucket = Config.S3_STORAGE_BUCKET
            parsed = urlparse(url)
            host = parsed.hostname or ""
            path = parsed.path or ""

            if host.startswith(f"{bucket}."):
                key = path.lstrip("/")
                return key or None

            prefix = f"/{bucket}/"
            if path.startswith(prefix):
                key = path[len(prefix) :]
                return key or None

            base = (Config.S3_STORAGE_PUBLIC_URL or "").rstrip("/")
            if base and not base.startswith("http://") and not base.startswith("https://"):
                base = "https://" + base
            if base:
                base_parsed = urlparse(base)
                base_path = base_parsed.path or ""
                if base_path == f"/{bucket}" and path.startswith(f"/{bucket}/"):
                    key = path[len(prefix) :]
                    return key or None
                if base_path.startswith(f"/{bucket}/") and path.startswith(base_path):
                    key = path[len(base_path) :].lstrip("/")
                    return key or None

            return None
        except Exception:
            return None

    def _looks_like_html_or_xml(self, head: bytes) -> bool:
        try:
            s = head.lstrip().lower()
            return s.startswith(b"<") or s.startswith(b"<!doctype html") or s.startswith(b"<?xml")
        except Exception:
            return False

    def _is_probably_mp4(self, file_path: str) -> bool:
        try:
            with open(file_path, "rb") as f:
                head = f.read(256)
            if not head:
                return False
            if self._looks_like_html_or_xml(head):
                return False
            return b"ftyp" in head[:128]
        except Exception:
            return False

    def _ffprobe_stream_info(self, file_path: str) -> dict | None:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,duration",
            "-of",
            "json",
            file_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            return None
        try:
            return json.loads(proc.stdout or "{}")
        except Exception:
            return None

    def _ffprobe_has_audio_stream(self, file_path: str) -> bool:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv=p=0",
            file_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            return False
        out = (proc.stdout or "").strip()
        return bool(out)

    def _probe_video_size(self, file_path: str) -> tuple[int, int] | None:
        info = self._ffprobe_stream_info(file_path)
        if not info:
            return None
        streams = info.get("streams") or []
        if not streams:
            return None
        s0 = streams[0] or {}
        w = s0.get("width")
        h = s0.get("height")
        try:
            w_i = int(w)
            h_i = int(h)
            if w_i > 0 and h_i > 0:
                return (w_i, h_i)
        except Exception:
            return None
        return None

    def _download_via_s3_if_possible(self, url: str, dest_path: str) -> bool:
        object_key = self._parse_object_key_from_public_url(url)
        if not object_key:
            return False
        try:
            self._s3_client.download_file(Config.S3_STORAGE_BUCKET, object_key, dest_path)
            return True
        except Exception:
            return False

    def _transcode_to_mp4(self, input_path: str) -> str | None:
        temp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        temp.close()
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-an",
            temp.name,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            try:
                os.remove(temp.name)
            except Exception:
                pass
            return None
        return temp.name

    def _open_video_clip(self, path: str):
        clip = None
        try:
            clip = VideoFileClip(path)
            if not getattr(clip, "duration", None) or clip.duration <= 0:
                raise OSError("video duration is 0")
            # Validate start
            _ = clip.get_frame(0)
            
            # Validate end (to ensure time_mirror won't crash)
            try:
                t_end = max(0.0, float(clip.duration) - 0.1)
                if t_end > 0:
                    _ = clip.get_frame(t_end)
            except Exception:
                raise OSError(f"Cannot read frame at end of video ({getattr(clip, 'duration', 'unknown')})")
            
            return clip
        except Exception:
            if clip is not None:
                try:
                    clip.close()
                except Exception:
                    pass
            raise

    def _placeholder_clip(self, duration: float, size: tuple[int, int] | None = None):
        safe_dur = max(0.1, float(duration or 0.0))
        clip = ColorClip(size=(size or (1280, 720)), color=(0, 0, 0), duration=safe_dur)
        return clip

    def render_video(self, timeline_assets: list, audio_map: dict, output_path: str) -> str:
        """
        Concatenate video clips based on timeline and add audio track.
        audio_map: dict { asset_id: local_audio_path }
        """
        final_clips = []
        temp_files_to_clean = []
        attached_audio_count = 0
        
        output_size = None
        pending_placeholders = []

        try:
            # 1. Process each asset
            for asset in timeline_assets:
                url = asset.get('oss_url')
                asset_id = asset.get('id')
                asset_duration = float(asset.get("duration") or 0.0)
                
                if not url and not asset.get("storage_key"):
                    continue
                    
                # Download Video
                local_video_path = self._download_temp(asset)
                temp_files_to_clean.append(local_video_path)
                
                try:
                    clip = self._open_video_clip(local_video_path)
                except Exception:
                    clip = None
                    
                # Basic resize to 720p height
                # Note: If mixed aspect ratios, this might be weird. 
                # Assuming all are vertical or we just fit height.
                if clip is not None and clip.h != 720:
                    clip = clip.resize(height=720)
                if clip is not None and output_size is None:
                    try:
                        output_size = tuple(clip.size)
                    except Exception:
                        output_size = None
                    if output_size is not None and pending_placeholders:
                        resized = []
                        for ph in pending_placeholders:
                            try:
                                resized.append(ph.resize(newsize=output_size))
                            except Exception:
                                resized.append(ph)
                        pending_placeholders.clear()
                        for i, c in enumerate(final_clips):
                            if getattr(c, "__placeholder__", False):
                                final_clips[i] = resized.pop(0) if resized else c
                
                # Get Audio
                audio_path = audio_map.get(asset_id) if audio_map else None
                
                if audio_path and os.path.exists(audio_path):
                    audio_clip = AudioFileClip(audio_path)
                    
                    # 3. Sync Logic (Elastic)
                    # Audio is the Master.
                    audio_dur = audio_clip.duration
                    if clip is None:
                        repaired = self._transcode_to_mp4(local_video_path)
                        if repaired:
                            temp_files_to_clean.append(repaired)
                            try:
                                clip = self._open_video_clip(repaired)
                            except Exception:
                                clip = None

                    if clip is None:
                        ph_size = output_size
                        if ph_size is None:
                            probed = self._probe_video_size(local_video_path)
                            if probed:
                                w, h = probed
                                if h > 0:
                                    ph_size = (max(1, int(round(w * 720.0 / float(h)))), 720)
                        clip = self._placeholder_clip(audio_dur or asset_duration or 5.0, size=ph_size)
                        setattr(clip, "__placeholder__", True)
                        if output_size is None:
                            pending_placeholders.append(clip)
                    video_dur = clip.duration
                    
                    # Elastic Match
                    if video_dur >= audio_dur:
                        # Video is longer -> Cut video
                        clip = clip.subclip(0, audio_dur)
                    else:
                        # Video is shorter -> Boomerang Extend
                        # Create a boomerang effect: Forward -> Backward -> Forward ...
                        
                        # Fix: trim a bit from the end to avoid EOF errors during time_mirror (reverse)
                        # Reading exactly at duration often fails in FFMPEG
                        safe_dur = max(0.1, clip.duration - 0.1)
                        if safe_dur < clip.duration:
                            clip = clip.subclip(0, safe_dur)
                            video_dur = clip.duration

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
                    attached_audio_count += 1
                else:
                    # No audio for this clip? 
                    # Keep original video duration or silence?
                    # Let's keep original video but without audio?
                    # Or maybe skip?
                    # Better to keep it to avoid missing visuals.
                    if clip is None:
                        clip = self._placeholder_clip(asset_duration or 5.0, size=output_size)
                        setattr(clip, "__placeholder__", True)
                        if output_size is None:
                            pending_placeholders.append(clip)
                
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
            if attached_audio_count <= 0:
                raise RuntimeError("render produced no audio-attached clips")
            if not self._ffprobe_has_audio_stream(output_path):
                raise RuntimeError("rendered mp4 has no audio stream")
            
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

    def _download_temp(self, asset) -> str:
        if isinstance(asset, str):
            url = asset
            asset = {"oss_url": url}
        url = asset.get("oss_url") or ""
        storage_type = (asset.get("storage_type") or "").upper()
        storage_key = asset.get("storage_key") or ""
        storage_bucket = asset.get("storage_bucket") or Config.S3_STORAGE_BUCKET
        local_path = asset.get("local_path") or ""

        if storage_type in {"LOCAL_FILE", "LOCAL"} and local_path:
            if os.path.exists(local_path):
                return local_path
            raise FileNotFoundError(local_path)

        if storage_type == "S3" and storage_key:
            temp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            temp.close()
            try:
                self._s3_client.download_file(storage_bucket, storage_key, temp.name)
                if not self._is_probably_mp4(temp.name):
                    raise OSError("downloaded file does not look like mp4")
                if not self._ffprobe_stream_info(temp.name):
                    raise OSError("downloaded mp4 failed ffprobe validation")
                return temp.name
            except Exception:
                if os.path.exists(temp.name):
                    os.remove(temp.name)
                raise

        if url.startswith("file://"):
            return url.replace("file://", "")
            
        temp = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        temp.close()
        try:
            if not url:
                raise ValueError("empty asset url")
            if url and self._download_via_s3_if_possible(url, temp.name):
                if not self._is_probably_mp4(temp.name):
                    raise OSError("downloaded file does not look like mp4")
                if not self._ffprobe_stream_info(temp.name):
                    raise OSError("downloaded mp4 failed ffprobe validation")
                return temp.name

            for attempt in range(1, 4):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "ai-scene-engine/1.0"})
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        with open(temp.name, "wb") as f:
                            while True:
                                chunk = resp.read(1024 * 1024)
                                if not chunk:
                                    break
                                f.write(chunk)
                    if not self._is_probably_mp4(temp.name):
                        raise OSError("downloaded file does not look like mp4")
                    if not self._ffprobe_stream_info(temp.name):
                        raise OSError("downloaded mp4 failed ffprobe validation")
                    break
                except (HTTPError, URLError, TimeoutError, OSError):
                    try:
                        if os.path.exists(temp.name):
                            os.remove(temp.name)
                    except Exception:
                        pass
                    temp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
                    temp.close()
                    if attempt < 3:
                        time.sleep(0.5 * attempt)
                        continue
                    raise
        except Exception:
            if os.path.exists(temp.name):
                os.remove(temp.name)
            raise
        return temp.name
