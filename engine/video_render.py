from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, vfx, ColorClip, afx, TextClip, CompositeVideoClip, CompositeAudioClip, ImageClip
from config import Config
from typing import List
import boto3
import dashscope
import numpy as np
from dashscope import Generation
from http import HTTPStatus
import json
import logging
import os
import re
import unicodedata
import subprocess
import tempfile
import time
import urllib.request
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Constants for intro/outro card generation
INTRO_TITLE_MAX_LENGTH = 12  # Maximum characters for intro title
SUBTITLE_MAX_LENGTH = 15  # Maximum characters for subtitle display
TITLE_FONT_SIZE_RATIO = 12  # video_width // ratio = font size
TAGLINE_FONT_SIZE_RATIO = 24
CTA_FONT_SIZE_RATIO = 15
CONTACT_FONT_SIZE_RATIO = 28
DEFAULT_FALLBACK_TITLE = '温馨之家'
DEFAULT_FALLBACK_TAGLINE = '用心感受，温暖生活'
DEFAULT_FALLBACK_CTA = ('预约看房，开启美好生活', '期待您的到来')
INTRO_BG_COLOR = (20, 20, 30)  # Dark blue-gray

# Intro voice script templates (开场白模板) - Fallback only
INTRO_VOICE_FALLBACK = "大家好，今天带大家看一套温馨的房子，跟我一起来感受一下吧！"

class VideoRenderer:
    def __init__(self, aliyun_client=None, sfx_library=None):
        self._s3_client = boto3.client(
            "s3",
            endpoint_url=Config.S3_STORAGE_ENDPOINT,
            aws_access_key_id=Config.S3_STORAGE_ACCESS_KEY,
            aws_secret_access_key=Config.S3_STORAGE_SECRET_KEY,
            region_name=Config.S3_STORAGE_REGION,
        )
        # Inject AliyunClient for AI enhancement
        self._aliyun_client = aliyun_client
        # Inject SFX Library for sound effects
        self._sfx_library = sfx_library

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

    def _apply_dynamic_speed_control(self, clip, asset: dict, asset_id: str):
        """
        Apply dynamic speed control based on emotion tag.
        
        Speed mapping strategy:
        - 惊艳 (stunning): 0.85x - Slow motion to highlight impact
        - 治愈/温馨 (healing/cozy): 0.90x - Gentle slow motion for warmth
        - 高级 (luxury): 0.95x - Micro slow motion for quality details
        - 普通 (normal): 1.0x - Normal speed
        - 过渡 (transition): 1.1x - Speed up for quick transitions
        
        Args:
            clip: VideoFileClip object
            asset: Asset dict with emotion/shock_score metadata
            asset_id: Asset ID for logging
            
        Returns:
            Modified clip with speed adjustment or original clip if disabled/failed
        """
        if not Config.DYNAMIC_SPEED_ENABLED:
            return clip
        
        try:
            # Extract emotion and shock_score
            emotion = asset.get('emotion', '').strip()
            shock_score = asset.get('shock_score', 0)
            recommended_speed = asset.get('recommended_speed')  # From vision analysis (Phase 2 enhancement)
            
            # Determine speed factor
            speed_factor = 1.0
            reasoning = "Default normal speed"
            
            if recommended_speed is not None:
                # Use AI-recommended speed if available (Phase 2 vision enhancement)
                speed_factor = float(recommended_speed)
                reasoning = asset.get('speed_reasoning', 'AI-recommended speed')
            else:
                # Fallback: Rule-based speed mapping
                if emotion == '惊艳' or shock_score >= 9:
                    speed_factor = Config.SPEED_MAP_STUNNING
                    reasoning = "Stunning visual - slow motion to highlight impact"
                elif emotion in ['治愈', '温馨', 'healing', 'cozy']:
                    speed_factor = Config.SPEED_MAP_COZY
                    reasoning = "Cozy/healing atmosphere - gentle slow motion"
                elif emotion in ['高级', '精致', 'luxury', 'elegant']:
                    speed_factor = Config.SPEED_MAP_LUXURY
                    reasoning = "Luxury/elegant - micro slow motion for details"
                elif emotion in ['过渡', 'transition'] or '走廊' in asset.get('scene_label', ''):
                    speed_factor = Config.SPEED_MAP_TRANSITION
                    reasoning = "Transition scene - speed up"
                else:
                    speed_factor = Config.SPEED_MAP_NORMAL
                    reasoning = "Normal scene - maintain flow"
            
            # Safety range (0.7x - 1.2x to avoid excessive distortion)
            speed_factor = max(0.7, min(1.2, speed_factor))
            
            # Apply speed adjustment if not normal speed
            if abs(speed_factor - 1.0) > 0.01:  # Only apply if meaningfully different
                original_duration = clip.duration
                clip = clip.fx(vfx.speedx, speed_factor)
                
                logger.info(
                    f"Applied dynamic speed control",
                    extra={
                        "event": "video.speed.dynamic",
                        "asset_id": asset_id,
                        "emotion": emotion,
                        "shock_score": shock_score,
                        "original_speed": 1.0,
                        "adjusted_speed": speed_factor,
                        "original_duration": original_duration,
                        "new_duration": clip.duration,
                        "reasoning": reasoning
                    }
                )
            
            return clip
            
        except Exception as e:
            logger.warning(f"Dynamic speed control failed for asset {asset_id}: {e}")
            return clip  # Return original clip on failure

    def _extend_with_last_frame(self, clip, target_duration: float):
        """
        Extend a video clip to target duration by freezing the last frame.
        More natural than boomerang (forward-backward looping).
        
        Args:
            clip: Original VideoFileClip
            target_duration: Target duration in seconds
        
        Returns:
            Extended clip with last frame frozen for the remaining time
        """
        try:
            current_dur = clip.duration
            if current_dur >= target_duration:
                return clip.subclip(0, target_duration)
            
            # Get the last frame
            last_frame_time = max(0, current_dur - 0.05)  # Slightly before end to avoid edge issues
            last_frame = clip.get_frame(last_frame_time)
            
            # Create a frozen frame clip for the remaining duration
            remaining = target_duration - current_dur
            freeze_clip = ImageClip(last_frame, duration=remaining)
            
            # Match size if needed
            if tuple(freeze_clip.size) != tuple(clip.size):
                freeze_clip = freeze_clip.resize(newsize=clip.size)
            
            # Concatenate original video with frozen frame
            extended = concatenate_videoclips([clip, freeze_clip])
            
            # Ensure exact duration
            if extended.duration > target_duration:
                extended = extended.subclip(0, target_duration)
            
            logger.info(
                f"Extended video with last frame freeze",
                extra={
                    "event": "video.extend.freeze",
                    "original_duration": current_dur,
                    "target_duration": target_duration,
                    "freeze_duration": remaining
                }
            )
            
            return extended
            
        except Exception as e:
            logger.warning(f"Last frame freeze failed: {e}, returning original clip")
            return clip

    def _apply_warm_filter(self, clip):
        """
        Apply a warm sunshine look using numpy:
        - Increase brightness/contrast slightly
        - Warm tint (Red++, Blue--)
        """
        try:
            def filter_warm(image):
                # image is numpy array [h, w, 3] (RGB)
                img = image.astype(float)
                # Warm tint: R*1.1, G*1.0, B*0.9
                img[:,:,0] *= 1.1 
                img[:,:,2] *= 0.9 
                # Slight Brightness increase
                img += 10.0
                np.clip(img, 0, 255, out=img)
                return img.astype('uint8')
            
            return clip.fl_image(filter_warm)
        except Exception:
            return clip

    def _get_combined_content_text(self, script_segments: list, house_info: dict) -> str:
        """
        Extract and combine all text content from script and house info.
        
        Args:
            script_segments: List of script segments
            house_info: Project metadata dict
        
        Returns:
            Combined text string for keyword matching
        """
        all_text = ' '.join([seg.get('text', '') for seg in script_segments]) if script_segments else ''
        description = house_info.get('description', '') if house_info else ''
        return f"{all_text} {description}"

    def _generate_intro_voice_script(self, house_info: dict, script_segments: list) -> str:
        """
        Generate intro voice-over script using LLM.
        
        使用大模型生成视频开场白文案，介绍房源基本信息。
        
        Args:
            house_info: Project metadata (title, description)
            script_segments: Script segments for context
        
        Returns:
            Voice script text for intro TTS
        """
        # Ensure dashscope API key is set
        if not Config.DASHSCOPE_API_KEY:
            logger.warning("DASHSCOPE_API_KEY not set, using fallback intro")
            return INTRO_VOICE_FALLBACK
        
        dashscope.api_key = Config.DASHSCOPE_API_KEY
        
        title = house_info.get('title', '').strip() if house_info else ''
        description = house_info.get('description', '').strip() if house_info else ''
        
        # Build context from script segments
        script_preview = ''
        if script_segments:
            first_texts = [seg.get('text', '')[:50] for seg in script_segments[:3] if seg.get('text')]
            script_preview = ' '.join(first_texts)
        
        # Build prompt for LLM
        prompt = f"""
# Role
你是一位专业的房产短视频主播，擅长"温情生活风"的开场白创作。

# Task
为一条房产看房视频撰写一段自然、亲切的开场白。开场白应该介绍这套房子的基本情况，让观众对要看的房子有个初步了解。

# 房源信息
- 标题: {title or '未提供'}
- 描述: {description or '未提供'}
- 视频内容预览: {script_preview or '未提供'}

# Style Guidelines
1. **口语化**: 像朋友聊天一样自然，不要僵硬的书面语
2. **热情亲切**: 带有热情，让人感觉被欢迎
3. **信息完整**: 尽可能包含小区名称/位置、户型（几室几厅）、亮点特色
4. **简洁明快**: 控制在 30-50 字以内，读起来 5-8 秒

# Constraints
- 必须以"大家好"或类似的问候开头
- 必须以引导用语结束，如"走，进去看看"、"跟我一起感受一下"
- 不要加任何标点符号外的装饰（如 emoji）
- 只输出开场白文本，不要输出其他内容

# Output Examples
例1: "大家好，今天带大家看的这套是位于滨江苑的三居室，采光特别棒，能看到江景。走，进去感受一下！"
例2: "嗨，朋友们好！今天这套房子在南山府，两室一厅，温馨舒适，特别适合小两口。来，带你们看看。"
例3: "大家好啊，今天给大家带来一套豪华大平层，180平的江景房，视野开阔。一起来感受一下这种品质感。"

# Action
请直接输出开场白文本，不要包含任何其他内容。
"""
        
        messages = [
            {'role': 'system', 'content': '你是一位专业的房产视频主播，输出简洁的开场白文案。'},
            {'role': 'user', 'content': prompt}
        ]
        
        try:
            response = Generation.call(
                model='qwen-plus',
                messages=messages,
                result_format='message',
                temperature=0.8  # Slightly higher for more natural variation
            )
            
            if response.status_code == HTTPStatus.OK:
                intro_script = response.output.choices[0].message.content.strip()
                
                # Clean up any extra quotes or markdown
                intro_script = intro_script.strip('"').strip("'").strip()
                if intro_script.startswith('“') and intro_script.endswith('”'):
                    intro_script = intro_script[1:-1]
                
                # Validate length (should be 20-80 chars)
                if len(intro_script) < 15 or len(intro_script) > 100:
                    logger.warning(
                        f"Generated intro script has unusual length ({len(intro_script)}), using fallback",
                        extra={"event": "intro.voice.length_warning", "length": len(intro_script)}
                    )
                    # Still use it if it seems valid
                    if len(intro_script) < 10:
                        return INTRO_VOICE_FALLBACK
                
                logger.info(
                    "Generated intro voice script via LLM",
                    extra={
                        "event": "intro.voice.llm_generated",
                        "script_length": len(intro_script),
                        "script_preview": intro_script[:50] if intro_script else None,
                    }
                )
                
                return intro_script
            else:
                logger.warning(
                    f"LLM call failed for intro script: {response.message}",
                    extra={"event": "intro.voice.llm_failed", "error": str(response.message)[:100]}
                )
                return INTRO_VOICE_FALLBACK
                
        except Exception as e:
            logger.warning(
                f"Failed to generate intro script via LLM: {e}",
                extra={"event": "intro.voice.llm_error", "error": str(e)[:100]}
            )
            return INTRO_VOICE_FALLBACK

    def _generate_intro_title_and_tagline(self, house_info: dict, script_segments: list) -> tuple[str, str]:
        """
        Generate intelligent title and tagline from video content.
        
        Strategy:
        1. Title: Extract from house_info title or summarize from first script segment
        2. Tagline: Extract emotional keywords from script content
        
        Args:
            house_info: Project metadata
            script_segments: Script segments for content analysis
        
        Returns:
            (title, tagline) tuple
        """
        # Extract title
        title = house_info.get('title', '').strip()
        if not title and script_segments:
            # Fallback: use first script segment as title
            first_seg = script_segments[0].get('text', '').strip()
            # Extract first sentence
            sentences = re.split(r'[。！？]', first_seg)
            title = sentences[0].strip() if sentences else DEFAULT_FALLBACK_TITLE
            # Limit length
            if len(title) > INTRO_TITLE_MAX_LENGTH:
                title = title[:INTRO_TITLE_MAX_LENGTH] + '...'
        
        if not title:
            title = DEFAULT_FALLBACK_TITLE
        
        # Generate tagline from script keywords
        tagline = self._extract_tagline_from_script(script_segments, house_info)
        
        return title, tagline
    
    def _extract_tagline_from_script(self, script_segments: list, house_info: dict) -> str:
        """
        Extract emotional tagline from script content.
        
        Strategy:
        - Analyze script keywords and scene descriptions
        - Match with predefined emotional templates
        - Generate contextual tagline
        
        Returns:
            Tagline string (fallback: DEFAULT_FALLBACK_TAGLINE)
        """
        if not script_segments:
            return DEFAULT_FALLBACK_TAGLINE
        
        # Get combined text for keyword matching
        combined_text = self._get_combined_content_text(script_segments, house_info)
        
        # Keyword-based tagline mapping
        tagline_patterns = [
            # View-based
            (['江景', '江边', '滨江'], '揽江景入怀，享都市繁华'),
            (['湖景', '湖畔'], '临湖而居，静享岁月'),
            (['海景', '海边'], '面朝大海，春暖花开'),
            (['山景', '山居'], '隐于山林，静谧致远'),
            
            # Atmosphere-based
            (['阳光', '采光', '明亮'], '阳光满屋，温暖相伴'),
            (['温馨', '温暖', '舒适'], '用心感受，温暖生活'),
            (['优雅', '精致', '高级'], '优雅生活，从此开始'),
            (['现代', '简约', '时尚'], '现代美学，理想栖居'),
            
            # Lifestyle-based
            (['家', '归家', '回家'], '家的温度，心的归属'),
            (['生活', '日常', '岁月'], '细品生活，慢享时光'),
            (['梦想', '理想', '憧憬'], '理想生活，触手可及'),
        ]
        
        # Match keywords
        for keywords, tagline in tagline_patterns:
            for keyword in keywords:
                if keyword in combined_text:
                    return tagline
        
        # Default fallback
        return DEFAULT_FALLBACK_TAGLINE
    
    def _create_intro_card(self, house_info: dict, script_segments: list, video_size: tuple[int, int], duration: float = 3.0, audio_clip=None, background_video=None, intro_card: dict = None) -> 'CompositeVideoClip':
        """
        Generate professional intro card with multi-layer information display.
        
        Uses first frame of the first video clip as a STATIC background image,
        with headline, specs, and highlights overlaid in a stacked layout.
        This design is inspired by high-performing real estate video covers.
        
        Args:
            house_info: Project metadata (title, description)
            script_segments: Script segments for content analysis
            video_size: Video resolution tuple (width, height)
            duration: Intro card duration in seconds (determined by voice-over length)
            audio_clip: Optional audio clip for voice-over
            background_video: Optional video clip to extract first frame from
            intro_card: Structured intro card data with headline, specs, highlights
        
        Returns:
            CompositeVideoClip with intro overlay
        """
        try:
            overlay_clips = []
            
            # Background selection: Use FIRST FRAME as static image
            if background_video is not None and Config.INTRO_USE_FIRST_VIDEO:
                try:
                    # Extract first frame as static image
                    first_frame = background_video.get_frame(0)
                    
                    # Create ImageClip from the first frame
                    bg_image = ImageClip(first_frame, duration=duration)
                    
                    # Resize to match target size if needed
                    if tuple(bg_image.size) != video_size:
                        bg_image = bg_image.resize(newsize=video_size)
                    
                    # Apply darkening effect for text readability
                    bg_image = bg_image.fx(vfx.colorx, 0.5)  # Darken to 50%
                    
                    overlay_clips.append(bg_image)
                    logger.info(f"Using first frame as static intro background (duration={duration:.2f}s)")
                except Exception as e:
                    logger.warning(f"Failed to extract first frame, falling back to solid color: {e}")
                    bg_clip = ColorClip(size=video_size, color=INTRO_BG_COLOR, duration=duration)
                    overlay_clips.append(bg_clip)
            else:
                # Solid color background
                bg_clip = ColorClip(size=video_size, color=INTRO_BG_COLOR, duration=duration)
                overlay_clips.append(bg_clip)
            
            # Check if we have structured intro_card data (new format)
            if intro_card and isinstance(intro_card, dict):
                # New multi-layer layout (inspired by high-performing covers)
                overlay_clips.extend(self._create_intro_card_layers(intro_card, video_size, duration))
                logger.info(f"Intro card (new format): headline='{intro_card.get('headline', '')}', specs='{intro_card.get('specs', '')}'")
            else:
                # Fallback to old title + tagline format
                title_text, tagline = self._generate_intro_title_and_tagline(house_info, script_segments)
                logger.info(f"Intro card (legacy): title='{title_text}', tagline='{tagline}'")
                
                # Main title
                try:
                    title_clip = TextClip(
                        title_text,
                        fontsize=min(80, video_size[0] // TITLE_FONT_SIZE_RATIO),
                        color='#F5F5DC',
                        font=Config.SUBTITLE_FONT,
                        stroke_color='#D4AF37',
                        stroke_width=2,
                        method='caption',
                        size=(video_size[0] * 0.8, None),
                        align='center'
                    )
                    title_clip = title_clip.set_position(('center', 0.35), relative=True)
                    title_clip = title_clip.set_duration(duration)
                    title_clip = title_clip.crossfadein(0.5).crossfadeout(0.3)
                    overlay_clips.append(title_clip)
                except Exception as e:
                    logger.warning(f"Failed to create intro title: {e}")
                
                # Tagline
                try:
                    tagline_clip = TextClip(
                        tagline,
                        fontsize=min(40, video_size[0] // TAGLINE_FONT_SIZE_RATIO),
                        color='white',
                        font=Config.SUBTITLE_FONT,
                        method='caption',
                        size=(video_size[0] * 0.7, None),
                        align='center'
                    )
                    tagline_clip = tagline_clip.set_position(('center', 0.50), relative=True)
                    tagline_clip = tagline_clip.set_duration(duration)
                    tagline_clip = tagline_clip.crossfadein(0.7).crossfadeout(0.3)
                    overlay_clips.append(tagline_clip)
                except Exception as e:
                    logger.warning(f"Failed to create intro tagline: {e}")
            
            # Create composite
            intro_composite = CompositeVideoClip(overlay_clips)
            
            # Attach audio if provided (voice-over determines duration)
            if audio_clip is not None:
                try:
                    intro_composite = intro_composite.set_audio(audio_clip)
                    logger.info(f"Attached voice-over audio to intro ({audio_clip.duration:.2f}s)")
                except Exception as e:
                    logger.warning(f"Failed to attach intro audio: {e}")
            
            return intro_composite
            
        except Exception as e:
            logger.error(f"Intro card generation failed: {e}")
            return ColorClip(size=video_size, color=(0, 0, 0), duration=duration)
    
    def _create_intro_card_layers(self, intro_card: dict, video_size: tuple[int, int], duration: float) -> list:
        """
        Create multi-layer text clips for the intro card.
        
        Layout (inspired by high-performing real estate video covers):
        - Headline: Large yellow text (location + community name)
        - Specs: Medium white text (size + layout)
        - Highlights: Stacked yellow tags (3 key selling points)
        
        Args:
            intro_card: Dict with headline, specs, highlights
            video_size: Video resolution
            duration: Clip duration
        
        Returns:
            List of TextClip objects
        """
        clips = []
        
        headline = intro_card.get('headline', '')
        specs = intro_card.get('specs', '')
        highlights = intro_card.get('highlights', [])
        
        # Color scheme (inspired by high-converting covers)
        HEADLINE_COLOR = '#FFD700'  # Gold/Yellow - eye-catching
        SPECS_COLOR = '#FFFFFF'     # White
        HIGHLIGHT_COLOR = '#FFE135' # Bright yellow
        STROKE_COLOR = '#000000'    # Black stroke for readability
        
        # Calculate positions (right-aligned, stacked vertically)
        # Layout: headline at ~25%, specs at ~38%, highlights starting at ~50%
        y_headline = 0.25
        y_specs = 0.38
        y_highlight_start = 0.50
        highlight_spacing = 0.08  # Vertical spacing between highlight tags
        
        # Headline - Large, bold, yellow
        if headline:
            try:
                headline_clip = TextClip(
                    headline,
                    fontsize=min(72, video_size[0] // 10),
                    color=HEADLINE_COLOR,
                    font=Config.SUBTITLE_FONT,
                    stroke_color=STROKE_COLOR,
                    stroke_width=3,
                    method='caption',
                    size=(video_size[0] * 0.85, None),
                    align='center'
                )
                headline_clip = headline_clip.set_position(('center', y_headline), relative=True)
                headline_clip = headline_clip.set_duration(duration)
                headline_clip = headline_clip.crossfadein(0.3).crossfadeout(0.2)
                clips.append(headline_clip)
            except Exception as e:
                logger.warning(f"Failed to create headline clip: {e}")
        
        # Specs - Medium, white
        if specs:
            try:
                specs_clip = TextClip(
                    specs,
                    fontsize=min(48, video_size[0] // 15),
                    color=SPECS_COLOR,
                    font=Config.SUBTITLE_FONT,
                    stroke_color=STROKE_COLOR,
                    stroke_width=2,
                    method='caption',
                    size=(video_size[0] * 0.8, None),
                    align='center'
                )
                specs_clip = specs_clip.set_position(('center', y_specs), relative=True)
                specs_clip = specs_clip.set_duration(duration)
                specs_clip = specs_clip.crossfadein(0.4).crossfadeout(0.2)
                clips.append(specs_clip)
            except Exception as e:
                logger.warning(f"Failed to create specs clip: {e}")
        
        # Highlights - Stacked yellow tags
        if highlights and isinstance(highlights, list):
            for i, highlight in enumerate(highlights[:3]):  # Max 3 highlights
                if not highlight:
                    continue
                try:
                    y_pos = y_highlight_start + (i * highlight_spacing)
                    highlight_clip = TextClip(
                        f"★ {highlight}",  # Add star prefix for visual appeal
                        fontsize=min(40, video_size[0] // 18),
                        color=HIGHLIGHT_COLOR,
                        font=Config.SUBTITLE_FONT,
                        stroke_color=STROKE_COLOR,
                        stroke_width=2,
                        method='caption',
                        size=(video_size[0] * 0.6, None),
                        align='center'
                    )
                    highlight_clip = highlight_clip.set_position(('center', y_pos), relative=True)
                    highlight_clip = highlight_clip.set_duration(duration)
                    # Staggered fade-in for visual interest
                    highlight_clip = highlight_clip.crossfadein(0.3 + i * 0.15).crossfadeout(0.2)
                    clips.append(highlight_clip)
                except Exception as e:
                    logger.warning(f"Failed to create highlight clip {i}: {e}")
        
        return clips
    
    def _generate_outro_cta(self, house_info: dict, script_segments: list) -> tuple[str, str]:
        """
        Generate intelligent CTA (Call-to-Action) for outro card.
        
        Strategy:
        - Analyze content to determine appropriate CTA
        - Match with property type and emotional tone
        
        Args:
            house_info: Project metadata
            script_segments: Script segments for content analysis
        
        Returns:
            (main_cta, sub_cta) tuple
        """
        if not script_segments:
            return DEFAULT_FALLBACK_CTA
        
        # Get combined text for keyword matching
        combined_text = self._get_combined_content_text(script_segments, house_info)
        
        # CTA patterns based on content keywords
        cta_patterns = [
            # View-based
            (['江景', '滨江'], ('与江景为伴，与美好相遇', '预约看房，感受不同')),
            (['湖景', '湖畔'], ('享受宁静，拥抱美好', '预约咨询，开启新生活')),
            (['海景'], ('面朝大海，心向自由', '立即预约，感受海景生活')),
            
            # Property type
            (['豪宅', '别墅', '豪华'], ('尊享生活，即刻开启', '私人预约，尊享服务')),
            (['大平层', '大屋'], ('空间自由，生活无限', '预约看房，体验大户型')),
            (['学区', '教育'], ('为孩子，选择更好未来', '预约参观，了解学区优势')),
            
            # Lifestyle
            (['温馨', '温暖'], ('回家，就是最好的时光', '预约看房，感受家的温度')),
            (['现代', '时尚'], ('现代生活，从这里开始', '立即预约，一探究竟')),
            (['优雅', '精致'], ('优雅品质，值得拥有', '预约咨询，品鉴美好')),
        ]
        
        # Match keywords
        for keywords, (main_cta, sub_cta) in cta_patterns:
            for keyword in keywords:
                if keyword in combined_text:
                    return main_cta, sub_cta
        
        # Default fallback
        return DEFAULT_FALLBACK_CTA
    
    def _create_outro_card(self, house_info: dict, script_segments: list, video_size: tuple[int, int], duration: float = 3.0) -> 'CompositeVideoClip':
        """
        Generate professional outro card with intelligent CTA.
        
        Args:
            house_info: Project metadata
            script_segments: Script segments for content analysis
            video_size: Video resolution tuple
            duration: Outro card duration in seconds
        
        Returns:
            CompositeVideoClip with outro overlay
        """
        try:
            # Background: Same elegant style as intro
            bg_clip = ColorClip(size=video_size, color=INTRO_BG_COLOR, duration=duration)
            
            overlay_clips = [bg_clip]
            
            # Generate intelligent CTA
            cta_text, contact_text = self._generate_outro_cta(house_info, script_segments)
            
            logger.info(f"Outro card: cta='{cta_text}', contact='{contact_text}'")
            
            # CTA Text
            try:
                cta_clip = TextClip(
                    cta_text,
                    fontsize=min(64, video_size[0] // CTA_FONT_SIZE_RATIO),
                    color='#F5F5DC',
                    font=Config.SUBTITLE_FONT,
                    stroke_color='#D4AF37',
                    stroke_width=2,
                    method='caption',
                    size=(video_size[0] * 0.8, None),
                    align='center'
                )
                cta_clip = cta_clip.set_position(('center', 0.35), relative=True)
                cta_clip = cta_clip.set_duration(duration)
                cta_clip = cta_clip.crossfadein(0.5).crossfadeout(0.8)
                overlay_clips.append(cta_clip)
            except Exception as e:
                logger.warning(f"Failed to create outro CTA: {e}")
            
            # Contact info or branding
            try:
                contact_clip = TextClip(
                    contact_text,
                    fontsize=min(36, video_size[0] // CONTACT_FONT_SIZE_RATIO),
                    color='white',
                    font=Config.SUBTITLE_FONT,
                    method='caption',
                    size=(video_size[0] * 0.7, None),
                    align='center'
                )
                contact_clip = contact_clip.set_position(('center', 0.50), relative=True)
                contact_clip = contact_clip.set_duration(duration)
                contact_clip = contact_clip.crossfadein(0.7).crossfadeout(0.8)
                overlay_clips.append(contact_clip)
            except Exception as e:
                logger.warning(f"Failed to create outro contact: {e}")
            
            return CompositeVideoClip(overlay_clips)
            
        except Exception as e:
            logger.error(f"Outro card generation failed: {e}")
            return ColorClip(size=video_size, color=(0, 0, 0), duration=duration)

    def _is_valid_subtitle_text(self, text: str) -> bool:
        """
        Check if text contains valid subtitle content (Chinese or meaningful English).
        Filters out pure numbers, pure punctuation, or empty strings.
        """
        if not text or not text.strip():
            return False
        
        cleaned = text.strip()
        
        # Filter out pure numbers (like "22")
        if cleaned.isdigit():
            return False
        
        # Filter out pure punctuation or special characters
        has_letter = False
        for char in cleaned:
            cat = unicodedata.category(char)
            # Lo = Letter, other (includes CJK); L* = Letters
            if cat.startswith('L'):
                has_letter = True
                break
        
        if not has_letter:
            return False
        
        # Minimum length requirement (at least 2 meaningful characters)
        letter_count = sum(1 for c in cleaned if unicodedata.category(c).startswith('L'))
        return letter_count >= 2

    def _generate_subtitle_clips(self, script_segments: list, video_size: tuple[int, int], time_offset: float = 0.0) -> list:
        """
        Generate subtitle TextClip objects from script segments.
        Supports multiple subtitle styles based on configuration.
        Returns list of positioned TextClip ready for composition.
        
        Args:
            script_segments: List of script segments with text and duration
            video_size: Video resolution tuple (width, height)
            time_offset: Time offset in seconds (e.g., intro duration)
        """
        subtitle_clips = []
        current_time = time_offset  # Start after intro if present
        
        # Define subtitle styles
        styles = {
            "default": {
                "fontsize": 48,
                "color": "white",
                "stroke_color": "black",
                "stroke_width": 2,
                "position": 0.75
            },
            "elegant": {
                "fontsize": 52,
                "color": "#F5F5DC",  # Beige white
                "stroke_color": "#8B7355",  # Brown shadow
                "stroke_width": 1.5,
                "position": 0.80
            },
            "bold": {
                "fontsize": 56,
                "color": "white",
                "stroke_color": "#D4AF37",  # Gold outline
                "stroke_width": 3,
                "position": 0.70
            }
        }
        
        # Get style from config or use default
        style_name = getattr(Config, 'SUBTITLE_STYLE', 'default')
        style = styles.get(style_name, styles['default'])
        
        for idx, seg in enumerate(script_segments):
            text = seg.get('text', '').strip()
            duration = float(seg.get('duration', 0.0))
            
            if not text or duration <= 0:
                current_time += duration
                continue
            
            # Extract key phrases for subtitle - try multiple sentences if first is invalid
            sentences = re.split(r'[。！？]', text)
            key_phrase = ''
            for sentence in sentences:
                candidate = sentence.strip()
                if self._is_valid_subtitle_text(candidate):
                    key_phrase = candidate
                    break
            
            # If no valid sentence found, try the full text
            if not key_phrase and self._is_valid_subtitle_text(text):
                key_phrase = text
            
            # Skip if still no valid subtitle content
            if not key_phrase:
                logger.debug(f"Skipping subtitle for segment {idx}: no valid text content")
                current_time += duration
                continue
            
            # Limit subtitle length for readability (use Chinese ellipsis)
            if len(key_phrase) > SUBTITLE_MAX_LENGTH:
                key_phrase = key_phrase[:SUBTITLE_MAX_LENGTH] + '……'
            
            try:
                # Final validation before rendering
                if not self._is_valid_subtitle_text(key_phrase):
                    logger.debug(f"Skipping invalid subtitle content for segment {idx}: '{key_phrase[:20]}'")
                    current_time += duration
                    continue
                
                # Create text clip
                txt_clip = TextClip(
                    key_phrase,
                    fontsize=style['fontsize'],
                    color=style['color'],
                    font=Config.SUBTITLE_FONT,
                    stroke_color=style['stroke_color'],
                    stroke_width=style['stroke_width'],
                    method='caption',
                    size=(video_size[0] * 0.8, None),
                    align='center'
                )
                
                # Position subtitle
                y_position = style['position']
                positioned = txt_clip.set_position(('center', y_position), relative=True)
                
                # Timing: show for appropriate duration
                show_duration = min(2.5, duration)
                positioned = positioned.set_start(current_time).set_duration(show_duration)
                
                # Enhanced transitions
                positioned = positioned.crossfadein(0.3).crossfadeout(0.3)
                
                subtitle_clips.append(positioned)
                
                logger.debug(
                    f"Created subtitle for segment {idx}",
                    extra={
                        "event": "subtitle.clip.created",
                        "segment_idx": idx,
                        "text_preview": key_phrase[:30],
                        "start_time": current_time,
                        "duration": show_duration
                    }
                )
                
            except Exception as e:
                logger.warning(f"Failed to create subtitle for segment {idx}: {e}")
            
            current_time += duration
        
        return subtitle_clips

    def _should_enhance_asset(self, asset: dict, index: int, total_count: int) -> bool:
        """
        Smart strategy to determine if an asset should use AI enhancement.
        Based on:
        - First clip (cover/thumbnail)
        - Assets with visual_prompt
        - Key moments (configurable)
        """
        if not Config.VISUAL_ENHANCEMENT_ENABLED:
            return False
        
        strategy = Config.VISUAL_ENHANCEMENT_STRATEGY
        
        if strategy == "all":
            return True
        elif strategy == "none":
            return False
        elif strategy == "smart":
            # Enhance first clip (cover)
            if index == 0:
                return True
            
            # Enhance if visual_prompt is explicitly provided
            visual_prompt = asset.get('visual_prompt', '').strip()
            if visual_prompt:
                return True
            
            # Enhance marked highlight clips
            if asset.get('is_highlight', False):
                return True
            
            return False
        
        return False

    def _enhance_video_with_ai(self, video_url: str, prompt: str) -> str:
        """
        Apply Aliyun Video Repainting to enhance visual style.
        Returns URL of enhanced video.
        """
        if not self._aliyun_client:
            logger.warning("AliyunClient not available, skipping AI enhancement")
            return video_url
        
        try:
            logger.info(f"Applying AI visual enhancement with prompt: {prompt[:50]}...")
            enhanced_url = self._aliyun_client.video_repainting(
                video_url, 
                prompt, 
                control_condition="depth"  # Preserve structure
            )
            logger.info(f"AI enhancement completed: {enhanced_url}")
            return enhanced_url
        except Exception as e:
            logger.error(f"AI enhancement failed, using original: {e}")
            return video_url

    def _build_enhancement_prompt(self, asset: dict, house_info: dict = None) -> str:
        """
        Build intelligent enhancement prompt based on asset context and house features.
        房源特征感知：根据房源类型、场景和特点动态生成最优 Prompt。
        """
        # Base prompt for warm life style
        base_prompt = "Warm sunshine, cinematic lighting, cozy atmosphere, 4k, high resolution"
        
        # Get scene label and custom visual prompt
        scene = asset.get('scene_label', '').lower()
        custom_prompt = asset.get('visual_prompt', '').strip()
        
        if custom_prompt:
            # If AI script already provided visual_prompt, use it directly
            return custom_prompt
        
        # Scene-specific enhancements
        scene_enhancements = {
            '客厅': 'spacious living room, natural light streaming through large windows, elegant furniture',
            'living': 'spacious living room, natural light streaming through large windows, elegant furniture',
            '卧室': 'serene bedroom, soft bedding, peaceful atmosphere, warm tones',
            'bedroom': 'serene bedroom, soft bedding, peaceful atmosphere, warm tones',
            '厨房': 'modern kitchen, clean white surfaces, bright and inviting, organized space',
            'kitchen': 'modern kitchen, clean white surfaces, bright and inviting, organized space',
            '阳台': 'balcony with city view, plants, relaxing outdoor space, golden hour',
            'balcony': 'balcony with city view, plants, relaxing outdoor space, golden hour',
            '餐厅': 'elegant dining area, warm lighting, family gathering space',
            'dining': 'elegant dining area, warm lighting, family gathering space',
        }
        
        # House feature keywords to enhance specific aspects
        feature_keywords = {
            '江景': 'river view, waterfront, panoramic scenery',
            '湖景': 'lake view, tranquil water scenery',
            '海景': 'ocean view, coastal atmosphere',
            '山景': 'mountain view, natural landscape',
            '学区': 'family-friendly, warm educational atmosphere',
            '豪华': 'luxury finishes, high-end materials, sophisticated design',
            '精装': 'modern renovation, tasteful decoration',
            '采光': 'abundant natural light, bright and airy',
            '通透': 'open layout, well-ventilated, spacious feeling',
        }
        
        # Build enhanced prompt
        prompt_parts = [base_prompt]
        
        # Add scene-specific enhancement
        for key, enhancement in scene_enhancements.items():
            if key in scene:
                prompt_parts.append(enhancement)
                break
        
        # Add house feature enhancements
        if house_info:
            title = house_info.get('title', '')
            description = house_info.get('description', '')
            combined_text = f"{title} {description}".lower()
            
            for keyword, enhancement in feature_keywords.items():
                if keyword in combined_text:
                    prompt_parts.append(enhancement)
                    break  # Only add one feature enhancement to avoid over-prompting
        
        return ', '.join(prompt_parts)

    def _apply_auto_ducking(self, tts_audio, bgm_audio, tts_segments: list) -> 'AudioClip':
        """
        Apply auto-ducking: reduce BGM volume when TTS is speaking.
        
        Args:
            tts_audio: The TTS audio track (already composite)
            bgm_audio: The background music track
            tts_segments: List of {'start': float, 'duration': float} for TTS segments
        
        Returns:
            Modified BGM audio with ducking applied
        """
        if not Config.AUTO_DUCKING_ENABLED or not tts_segments:
            return bgm_audio
        
        try:
            # Build ducking envelope
            # During TTS: reduce to ducking_level (e.g. 30%)
            # Outside TTS: normal BGM_VOLUME (e.g. 15%)
            
            total_duration = bgm_audio.duration
            ducking_level = Config.BGM_DUCKING_LEVEL  # e.g. 0.3
            normal_level = 1.0  # BGM is already at BGM_VOLUME, so this is relative
            
            # Create volume envelope function
            def volume_envelope(t):
                # Check if current time is within any TTS segment
                for seg in tts_segments:
                    start = seg.get('start', 0.0)
                    duration = seg.get('duration', 0.0)
                    end = start + duration
                    
                    # Add fade transition zones (0.2s)
                    fade_time = 0.2
                    
                    if start <= t <= end:
                        # Within TTS segment
                        if t < start + fade_time:
                            # Fade down
                            ratio = (t - start) / fade_time
                            return normal_level - (normal_level - ducking_level) * ratio
                        elif t > end - fade_time:
                            # Fade up
                            ratio = (end - t) / fade_time
                            return ducking_level + (normal_level - ducking_level) * (1 - ratio)
                        else:
                            # Full duck
                            return ducking_level
                
                return normal_level
            
            # Apply volume envelope
            ducked_bgm = bgm_audio.fl(lambda gf, t: gf(t) * volume_envelope(t), apply_to=['audio'])
            
            logger.info(f"Auto-ducking applied to BGM with {len(tts_segments)} TTS segments")
            return ducked_bgm
            
        except Exception as e:
            logger.warning(f"Auto-ducking failed, using original BGM: {e}")
            return bgm_audio
    
    def _apply_dynamic_volume_curve(self, bgm_clip, video_duration: float, intensity_curve: List[float] = None) -> 'AudioClip':
        """
        应用动态音量曲线到BGM（Phase 2-2新增）
        
        Args:
            bgm_clip: 原始BGM音频
            video_duration: 视频总时长
            intensity_curve: 音量曲线（5段归一化值，如[0.1, 0.3, 0.35, 0.3, 0.2]）
        
        Returns:
            应用动态音量后的BGM
        """
        if not Config.BGM_DYNAMIC_VOLUME_ENABLED:
            return bgm_clip
        
        # Default 5-segment curve if not provided
        if not intensity_curve:
            intensity_curve = [0.15, 0.2, 0.25, 0.2, 0.15]  # Gentle default curve
        
        # Ensure we have exactly 5 segments
        if len(intensity_curve) != 5:
            logger.warning(f"Intensity curve must have 5 values, got {len(intensity_curve)}. Using default.")
            intensity_curve = [0.15, 0.2, 0.25, 0.2, 0.15]
        
        try:
            # 将视频分为5段
            segment_duration = video_duration / 5.0
            
            def volume_envelope(t):
                """
                根据时间t返回音量系数
                
                音量曲线设计：
                - Segment 1 (0-20%): 开场 - 低音量渐入
                - Segment 2 (20-40%): 缓升 - 逐渐提升
                - Segment 3 (40-60%): 高潮 - 最高音量
                - Segment 4 (60-80%): 收尾 - 降低音量
                - Segment 5 (80-100%): 结束 - 渐出
                """
                segment_index = min(int(t / segment_duration), 4)
                current_intensity = intensity_curve[segment_index]
                
                # Smooth transition between segments using linear interpolation
                next_index = min(segment_index + 1, 4)
                segment_start = segment_index * segment_duration
                segment_progress = (t - segment_start) / segment_duration
                
                if segment_index < 4:
                    next_intensity = intensity_curve[next_index]
                    # Linear interpolation
                    interpolated_intensity = current_intensity + (next_intensity - current_intensity) * segment_progress
                else:
                    interpolated_intensity = current_intensity
                
                # Multiply by base BGM volume
                return interpolated_intensity * Config.BGM_VOLUME
            
            # Apply volume envelope using MoviePy's volumex with function
            bgm_with_curve = bgm_clip.fl(lambda gf, t: gf(t) * (volume_envelope(t) / Config.BGM_VOLUME), apply_to=['audio'])
            
            logger.info(
                f"Applied dynamic volume curve to BGM",
                extra={
                    "event": "bgm.volume.dynamic",
                    "video_duration": video_duration,
                    "curve": intensity_curve,
                    "segment_duration": segment_duration
                }
            )
            
            return bgm_with_curve
            
        except Exception as e:
            logger.warning(f"Dynamic volume curve failed: {e}")
            return bgm_clip

    def _generate_sfx_tracks(self, script_segments: list, video_duration: float) -> list:
        """
        Generate sound effect audio tracks based on audio_cue in script segments.
        Returns list of AudioFileClip objects positioned at correct timestamps.
        """
        if not Config.SFX_ENABLED or not self._sfx_library:
            return []
        
        if not self._sfx_library.is_available():
            logger.warning("SFX library not available, skipping sound effects")
            return []
        
        sfx_clips = []
        current_time = 0.0
        
        for seg in script_segments:
            audio_cue = seg.get('audio_cue', '').strip()
            duration = float(seg.get('duration', 0.0))
            
            if audio_cue:
                sfx_path = self._sfx_library.get_sfx_path(audio_cue)
                
                if sfx_path:
                    try:
                        sfx_clip = AudioFileClip(sfx_path)
                        
                        # Position at start of segment
                        sfx_clip = sfx_clip.set_start(current_time)
                        
                        # Reduce volume to blend naturally (30% of original)
                        sfx_clip = sfx_clip.volumex(0.3)
                        
                        # Trim if SFX is longer than segment
                        if sfx_clip.duration > duration:
                            sfx_clip = sfx_clip.subclip(0, duration)
                        
                        sfx_clips.append(sfx_clip)
                        logger.info(f"Added SFX '{audio_cue}' at {current_time:.1f}s")
                        
                    except Exception as e:
                        logger.warning(f"Failed to load SFX '{audio_cue}': {e}")
            
            current_time += duration
        
        return sfx_clips

    def _select_opening_highlight_shot(self, timeline_assets: list, script_segments: list = None) -> dict | None:
        """
        Select the best highlight shot for opening hook (first 3 seconds).
        
        Algorithm:
        1. Filter candidates with shock_score >= 8
        2. Priority ranking:
           - P0: Emotion="惊艳" (stunning views/features)
           - P1: Super large space (客厅>40㎡, 主卧>25㎡)
           - P2: Unique design (island counter, walk-in closet, terrace)
        3. Extract the most impactful 1-3 seconds from selected segment
        4. Mark segment as "used_in_hook" to avoid duplication
        
        Returns:
            dict with keys: source_asset, extract_start, extract_duration, segment_index
            or None if no suitable highlight found
        """
        if not timeline_assets:
            return None
        
        # Extract segment metadata from script_segments if available
        segment_metadata = {}
        if script_segments:
            for idx, seg in enumerate(script_segments):
                asset_id = seg.get('asset_id')
                if asset_id:
                    segment_metadata[asset_id] = {
                        'shock_score': seg.get('shock_score', 0),
                        'emotion': seg.get('emotion', ''),
                        'features': seg.get('features', ''),
                        'segment_index': idx
                    }
        
        # Build candidates list
        candidates = []
        for idx, asset in enumerate(timeline_assets):
            asset_id = asset.get('id')
            
            # Get shock_score from metadata or asset itself
            shock_score = 0
            emotion = ''
            features = ''
            
            if asset_id in segment_metadata:
                meta = segment_metadata[asset_id]
                shock_score = meta.get('shock_score', 0)
                emotion = meta.get('emotion', '')
                features = meta.get('features', '')
            else:
                # Fallback: try to get from asset directly
                shock_score = asset.get('shock_score', 0)
                emotion = asset.get('emotion', '')
                features = asset.get('features', '')
            
            # Filter: shock_score >= 8
            if shock_score >= 8:
                # Calculate priority score
                priority = 0
                if emotion == '惊艳':
                    priority = 100  # P0: Stunning emotion
                elif '超大' in features or '270' in features or '江景' in features:
                    priority = 80   # P1: Spectacular views/space
                elif '衣帽间' in features or '岛台' in features or '露台' in features:
                    priority = 60   # P2: Unique design features
                else:
                    priority = shock_score * 5  # Base on shock_score
                
                candidates.append({
                    'asset': asset,
                    'asset_index': idx,
                    'shock_score': shock_score,
                    'emotion': emotion,
                    'features': features,
                    'priority': priority
                })
        
        if not candidates:
            logger.info("No high-shock segments (score>=8) found for opening hook")
            return None
        
        # Sort by priority (highest first), then by shock_score, then by position (later is better for suspense)
        candidates.sort(key=lambda c: (c['priority'], c['shock_score'], c['asset_index']), reverse=True)
        
        best = candidates[0]
        best_asset = best['asset']
        asset_duration = float(best_asset.get('duration', 0))
        
        # Extract optimal clip duration (2-3 seconds for hook)
        hook_duration = min(3.0, max(2.0, asset_duration))
        
        # Extract from the most visually impactful part (usually middle or start)
        # For stunning views, start from beginning; for reveals, use middle
        if best['emotion'] == '惊艳' or '景观' in best['features']:
            extract_start = 0.0  # Immediate visual impact
        else:
            # Use middle section for dramatic reveal
            extract_start = max(0, (asset_duration - hook_duration) / 2)
        
        result = {
            'source_asset': best_asset,
            'extract_start': extract_start,
            'extract_duration': min(hook_duration, asset_duration - extract_start),
            'segment_index': best['asset_index'],
            'shock_score': best['shock_score'],
            'emotion': best['emotion']
        }
        
        logger.info(
            f"Selected highlight shot for opening hook",
            extra={
                "event": "opening_hook.highlight_selected",
                "asset_id": best_asset.get('id'),
                "shock_score": best['shock_score'],
                "emotion": best['emotion'],
                "extract_start": extract_start,
                "extract_duration": result['extract_duration']
            }
        )
        
        return result
    
    def render_video(self, timeline_assets: list, audio_map: dict, output_path: str, bgm_path: str = None, script_segments: list = None, house_info: dict = None, audio_gen=None, intro_text: str = None, intro_card: dict = None, bgm_metadata: dict = None) -> str:
        """
        Concatenate video clips based on timeline and add audio track.
        audio_map: dict { asset_id: local_audio_path }
        bgm_path: optional path to background music file
        script_segments: optional list of script segments for subtitle generation
        house_info: optional house information for intelligent AI enhancement
        audio_gen: optional AudioGenerator instance for intro voice generation
        intro_text: optional user-edited intro voice-over text (takes precedence over auto-generation)
        intro_card: optional structured intro card data with headline, specs, highlights
        bgm_metadata: optional BGM metadata dict with intensity_curve (Phase 2-2 new feature)
        """
        final_clips = []
        temp_files_to_clean = []
        attached_audio_count = 0
        
        output_size = None
        pending_placeholders = []

        try:
            # 1. Process each asset
            for idx, asset in enumerate(timeline_assets):
                url = asset.get('oss_url')
                asset_id = asset.get('id')
                asset_duration = float(asset.get("duration") or 0.0)
                visual_prompt = asset.get('visual_prompt', '').strip()
                
                # --- AI Visual Enhancement (P0 Feature) ---
                if self._should_enhance_asset(asset, idx, len(timeline_assets)):
                    # Build intelligent prompt based on scene and house features
                    enhance_prompt = self._build_enhancement_prompt(asset, house_info)
                    
                    try:
                        enhanced_url = self._enhance_video_with_ai(url, enhance_prompt)
                        # Replace URL with enhanced version
                        asset = {**asset, 'oss_url': enhanced_url}
                        url = enhanced_url
                        logger.info(f"Asset {asset_id} enhanced with AI (index={idx}, prompt={enhance_prompt[:50]}...)")
                    except Exception as e:
                        logger.warning(f"AI enhancement failed for asset {asset_id}, using original: {e}")
                # ------------------------------------------
                
                if not url and not asset.get("storage_key"):
                    continue
                    
                # Download Video
                local_video_path = self._download_temp(asset)
                temp_files_to_clean.append(local_video_path)
                
                try:
                    clip = self._open_video_clip(local_video_path)
                    # Apply Warm Filter (Global for "Warm Life Style")
                    clip = self._apply_warm_filter(clip)
                    
                    # --- Phase 2-1: Dynamic Speed Control (Emotion-based) ---
                    clip = self._apply_dynamic_speed_control(clip, asset, asset_id)
                    # ---------------------------------------------------------
                except Exception as video_error:
                    logger.error(
                        f"Failed to open video clip for asset {asset_id}",
                        extra={
                            "event": "video.clip.open_failed",
                            "asset_id": asset_id,
                            "error_type": type(video_error).__name__,
                            "error_message": str(video_error)[:200]
                        }
                    )
                    clip = None
                    
                # Basic resize to 720p height
                # Note: If mixed aspect ratios, this might be weird. 
                # Assuming all are vertical or we just fit height.
                target_height = min(720, Config.MAX_VIDEO_RESOLUTION)
                if clip is not None and clip.h != target_height:
                    clip = clip.resize(height=target_height)
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
                        # Video is shorter -> Use slow motion + last frame freeze
                        # This is more natural than boomerang (forward-backward looping)
                        
                        gap = audio_dur - video_dur
                        
                        # Strategy: 
                        # 1. If gap is small (<30% of video), use gentle slow motion
                        # 2. If gap is larger, use slow motion + last frame freeze
                        
                        if gap <= video_dur * 0.3:
                            # Small gap: gentle slow motion (0.77x - 1.0x)
                            speed_factor = video_dur / audio_dur
                            speed_factor = max(0.77, speed_factor)  # Don't go slower than 0.77x
                            
                            try:
                                clip = clip.fx(vfx.speedx, speed_factor)
                                # Trim to exact duration
                                if clip.duration > audio_dur:
                                    clip = clip.subclip(0, audio_dur)
                                logger.info(
                                    f"Applied slow motion to extend video",
                                    extra={
                                        "event": "video.extend.slowmo",
                                        "asset_id": asset_id,
                                        "speed_factor": speed_factor,
                                        "original_duration": video_dur,
                                        "target_duration": audio_dur
                                    }
                                )
                            except Exception as e:
                                logger.warning(f"Slow motion failed, using last frame freeze: {e}")
                                clip = self._extend_with_last_frame(clip, audio_dur)
                        else:
                            # Larger gap: slow motion (0.85x) + last frame freeze for remainder
                            try:
                                # Apply moderate slow motion first
                                slow_factor = 0.85
                                slowed_clip = clip.fx(vfx.speedx, slow_factor)
                                slowed_dur = slowed_clip.duration
                                
                                if slowed_dur >= audio_dur:
                                    # Slow motion alone is enough
                                    clip = slowed_clip.subclip(0, audio_dur)
                                else:
                                    # Need last frame freeze for the rest
                                    remaining = audio_dur - slowed_dur
                                    clip = self._extend_with_last_frame(slowed_clip, audio_dur)
                                
                                logger.info(
                                    f"Applied slow motion + freeze to extend video",
                                    extra={
                                        "event": "video.extend.slowmo_freeze",
                                        "asset_id": asset_id,
                                        "slow_factor": slow_factor,
                                        "original_duration": video_dur,
                                        "target_duration": audio_dur
                                    }
                                )
                            except Exception as e:
                                logger.warning(f"Slow motion + freeze failed, using simple freeze: {e}")
                                clip = self._extend_with_last_frame(clip, audio_dur)
                    
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

            # 4. Concatenate All Video Clips
            main_video = concatenate_videoclips(final_clips, method="compose")
            
            # Determine video size for intro/outro
            video_size = tuple(main_video.size) if hasattr(main_video, 'size') else (1280, 720)
            
            # 5. Add Intro and Outro Cards
            all_video_parts = []
            intro_card = None
            outro_card = None
            intro_audio_path = None  # Track for cleanup
            first_video_clip = None  # For intro background
            
            # Get first video clip for intro background (before it's modified)
            if Config.INTRO_ENABLED and Config.INTRO_USE_FIRST_VIDEO and final_clips:
                try:
                    # Clone first clip for intro background
                    first_clip = final_clips[0]
                    if first_clip is not None and not getattr(first_clip, "__placeholder__", False):
                        first_video_clip = first_clip.copy()
                        logger.info("Prepared first video clip for intro background")
                except Exception as e:
                    logger.warning(f"Failed to prepare first video clip for intro: {e}")
                    first_video_clip = None
            
            # Intro Card (with optional voice-over)
            if Config.INTRO_ENABLED:
                try:
                    intro_duration = Config.INTRO_DURATION
                    intro_audio_clip = None
                    
                    # Generate intro voice-over if enabled
                    if Config.INTRO_VOICE_ENABLED and audio_gen is not None:
                        try:
                            # Use user-edited intro text if provided, otherwise generate
                            if intro_text and intro_text.strip():
                                intro_script = intro_text.strip()
                                logger.info(f"Using user-provided intro text: '{intro_script[:50]}...'")
                            else:
                                # Generate intro voice script via LLM
                                intro_script = self._generate_intro_voice_script(house_info or {}, script_segments or [])
                            
                            if intro_script:
                                # Generate TTS audio for intro
                                intro_audio_path = os.path.join(
                                    tempfile.gettempdir(), 
                                    f"intro_voice_{int(time.time())}.mp3"
                                )
                                audio_gen.generate_audio(intro_script, intro_audio_path)
                                
                                if os.path.exists(intro_audio_path):
                                    intro_audio_clip = AudioFileClip(intro_audio_path)
                                    # Intro duration is based on voice duration + small buffer
                                    intro_duration = intro_audio_clip.duration + 0.5
                                    logger.info(
                                        f"Generated intro voice: duration={intro_audio_clip.duration:.2f}s, script='{intro_script[:50]}...'"
                                    )
                        except Exception as e:
                            logger.warning(f"Failed to generate intro voice, using static intro: {e}")
                            intro_audio_clip = None
                    
                    intro_clip = self._create_intro_card(
                        house_info or {}, 
                        script_segments or [], 
                        video_size, 
                        duration=intro_duration,
                        audio_clip=intro_audio_clip,
                        background_video=first_video_clip,
                        intro_card=intro_card  # Pass structured intro card data
                    )
                    all_video_parts.append(intro_clip)
                    logger.info(f"Intro card added successfully ({intro_duration:.2f}s, voice={intro_audio_clip is not None})")
                except Exception as e:
                    logger.warning(f"Failed to add intro card: {e}")
                    intro_clip = None
            
            # Main video content
            all_video_parts.append(main_video)
            
            # Outro Card (configurable duration)
            if Config.OUTRO_ENABLED:
                try:
                    outro_duration = Config.OUTRO_DURATION
                    outro_card = self._create_outro_card(
                        house_info or {}, 
                        script_segments or [], 
                        video_size, 
                        duration=outro_duration
                    )
                    all_video_parts.append(outro_card)
                    logger.info(f"Outro card added successfully ({outro_duration}s)")
                except Exception as e:
                    logger.warning(f"Failed to add outro card: {e}")
                    outro_card = None
            
            # Concatenate all parts (intro + main + outro)
            final_video = concatenate_videoclips(all_video_parts, method="compose")
            
            # Calculate actual intro duration for subtitle offset
            actual_intro_duration = 0.0
            if intro_clip is not None:
                try:
                    actual_intro_duration = intro_clip.duration
                except Exception:
                    actual_intro_duration = Config.INTRO_DURATION if Config.INTRO_ENABLED else 0.0

            # --- Subtitle Integration (P0 Feature) ---
            if script_segments and Config.SUBTITLE_ENABLED:
                try:
                    # Calculate time offset for subtitles (after intro)
                    subtitle_offset = actual_intro_duration
                    
                    logger.info(
                        "Starting subtitle generation",
                        extra={
                            "event": "subtitle.generation.start",
                            "segment_count": len(script_segments),
                            "video_duration": float(final_video.duration),
                            "time_offset": subtitle_offset
                        }
                    )
                    video_size = tuple(final_video.size) if hasattr(final_video, 'size') else (1280, 720)
                    subtitle_clips = self._generate_subtitle_clips(script_segments, video_size, time_offset=subtitle_offset)
                    
                    if subtitle_clips:
                        logger.info(
                            f"Adding {len(subtitle_clips)} subtitle clips to video",
                            extra={
                                "event": "subtitle.integration.success",
                                "subtitle_count": len(subtitle_clips)
                            }
                        )
                        final_video = CompositeVideoClip([final_video] + subtitle_clips)
                except Exception as e:
                    logger.warning(
                        f"Subtitle rendering failed, continuing without subtitles",
                        extra={
                            "event": "subtitle.rendering.failed",
                            "error_type": type(e).__name__,
                            "error_message": str(e)[:200]
                        }
                    )
            # ------------------------------------------

            # --- Audio Mixing (TTS + BGM + SFX) ---
            audio_tracks = []
            if final_video.audio:
                audio_tracks.append(final_video.audio)
            
            # --- SFX Integration (P1 Feature) ---
            if Config.SFX_ENABLED and script_segments:
                try:
                    sfx_clips = self._generate_sfx_tracks(script_segments, final_video.duration)
                    if sfx_clips:
                        logger.info(f"Adding {len(sfx_clips)} sound effects to audio mix")
                        audio_tracks.extend(sfx_clips)
                except Exception as e:
                    logger.warning(f"SFX generation failed: {e}")
            # ------------------------------------
            
            if bgm_path and os.path.exists(bgm_path):
                try:
                    bgm_clip = AudioFileClip(bgm_path)
                    # Loop BGM if shorter
                    if bgm_clip.duration < final_video.duration:
                        bgm_clip = bgm_clip.fx(afx.audio_loop, duration=final_video.duration)
                    else:
                        bgm_clip = bgm_clip.subclip(0, final_video.duration)
                    
                    # --- Phase 2-2: Dynamic Volume Curve ---
                    if bgm_metadata and Config.BGM_DYNAMIC_VOLUME_ENABLED:
                        # Use BGM metadata intensity curve if available
                        intensity_curve = bgm_metadata.get('intensity_curve', [0.15, 0.2, 0.25, 0.2, 0.15])
                        bgm_clip = self._apply_dynamic_volume_curve(bgm_clip, final_video.duration, intensity_curve)
                        logger.info(f"Applied dynamic volume curve from BGM metadata")
                    else:
                        # Fallback: Static volume control
                        bgm_clip = bgm_clip.volumex(Config.BGM_VOLUME)
                    # ----------------------------------------
                    
                    # --- Auto-ducking (P1 Feature) ---
                    if Config.AUTO_DUCKING_ENABLED and script_segments:
                        # Build TTS segment timing info
                        tts_timing = []
                        current_time = 0.0
                        for seg in script_segments:
                            duration = float(seg.get('duration', 0.0))
                            if seg.get('text', '').strip():  # Only segments with text
                                tts_timing.append({'start': current_time, 'duration': duration})
                            current_time += duration
                        
                        bgm_clip = self._apply_auto_ducking(final_video.audio, bgm_clip, tts_timing)
                    # ------------------------------------
                    
                    audio_tracks.append(bgm_clip)
                except Exception as e:
                    logger.warning(f"Failed to load BGM: {e}")

            if len(audio_tracks) > 1:
                final_audio = CompositeAudioClip(audio_tracks)
                final_video = final_video.set_audio(final_audio)
            # --------------------------------

            # 5. Write Output
            final_video.write_videofile(
                output_path, 
                codec='libx264', 
                audio_codec='aac', 
                fps=24,
                preset='veryfast',
                threads=Config.RENDER_THREADS,  # Configurable thread count
                logger=None 
            )
            if attached_audio_count <= 0:
                raise RuntimeError("render produced no audio-attached clips")
            if not self._ffprobe_has_audio_stream(output_path):
                raise RuntimeError("rendered mp4 has no audio stream")
            
        finally:
            # Cleanup video clips
            for clip in final_clips:
                try:
                    clip.close()
                    if clip.audio: 
                        clip.audio.close()
                except Exception:
                    pass
            
            # Cleanup intro/outro cards
            for card in [intro_clip, outro_card]:
                if card is not None:
                    try:
                        card.close()
                    except Exception:
                        pass
            
            # Cleanup first video clip (intro background)
            if first_video_clip is not None:
                try:
                    first_video_clip.close()
                except Exception:
                    pass
            
            # Cleanup intro audio temp file
            if intro_audio_path and os.path.exists(intro_audio_path):
                try:
                    os.remove(intro_audio_path)
                except Exception:
                    pass
            
            # Cleanup temp files
            for p in temp_files_to_clean:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
                
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
