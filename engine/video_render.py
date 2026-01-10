from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, vfx, ColorClip, afx, TextClip, CompositeVideoClip, CompositeAudioClip
from config import Config
import boto3
import json
import logging
import os
import re
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

    def _apply_warm_filter(self, clip):
        """
        Apply a warm sunshine look using numpy:
        - Increase brightness/contrast slightly
        - Warm tint (Red++, Blue--)
        """
        try:
            def filter_warm(image):
                # image is numpy array [h, w, 3] (RGB)
                import numpy as np
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
    
    def _create_intro_card(self, house_info: dict, script_segments: list, video_size: tuple[int, int], duration: float = 3.0) -> 'CompositeVideoClip':
        """
        Generate professional intro card with intelligent title and tagline.
        
        Args:
            house_info: Project metadata (title, description)
            script_segments: Script segments for content analysis
            video_size: Video resolution tuple (width, height)
            duration: Intro card duration in seconds
        
        Returns:
            CompositeVideoClip with intro overlay
        """
        try:
            # Background: Elegant gradient or solid color
            bg_clip = ColorClip(size=video_size, color=INTRO_BG_COLOR, duration=duration)
            
            overlay_clips = [bg_clip]
            
            # Generate intelligent title and tagline
            title_text, tagline = self._generate_intro_title_and_tagline(house_info, script_segments)
            
            logger.info(f"Intro card: title='{title_text}', tagline='{tagline}'")
            
            # Main title
            try:
                title_clip = TextClip(
                    title_text,
                    fontsize=min(80, video_size[0] // TITLE_FONT_SIZE_RATIO),
                    color='#F5F5DC',  # Beige white
                    font=Config.SUBTITLE_FONT,
                    stroke_color='#D4AF37',  # Gold outline
                    stroke_width=2,
                    method='caption',
                    size=(video_size[0] * 0.8, None),
                    align='center'
                )
                title_clip = title_clip.set_position(('center', 0.35), relative=True)
                title_clip = title_clip.set_duration(duration)
                title_clip = title_clip.crossfadein(0.8).crossfadeout(0.5)
                overlay_clips.append(title_clip)
            except Exception as e:
                logger.warning(f"Failed to create intro title: {e}")
            
            # Tagline / Subtitle
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
                tagline_clip = tagline_clip.crossfadein(1.0).crossfadeout(0.5)
                overlay_clips.append(tagline_clip)
            except Exception as e:
                logger.warning(f"Failed to create intro tagline: {e}")
            
            return CompositeVideoClip(overlay_clips)
            
        except Exception as e:
            logger.error(f"Intro card generation failed: {e}")
            # Fallback: simple black clip
            return ColorClip(size=video_size, color=(0, 0, 0), duration=duration)
    
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
            
            # Extract key phrases for subtitle
            sentences = re.split(r'[。！？]', text)
            key_phrase = sentences[0].strip() if sentences else text
            
            # Limit subtitle length for readability
            if len(key_phrase) > SUBTITLE_MAX_LENGTH:
                key_phrase = key_phrase[:SUBTITLE_MAX_LENGTH] + '...'
            
            try:
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
            import numpy as np
            
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

    def render_video(self, timeline_assets: list, audio_map: dict, output_path: str, bgm_path: str = None, script_segments: list = None, house_info: dict = None) -> str:
        """
        Concatenate video clips based on timeline and add audio track.
        audio_map: dict { asset_id: local_audio_path }
        bgm_path: optional path to background music file
        script_segments: optional list of script segments for subtitle generation
        house_info: optional house information for intelligent AI enhancement
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

            # 4. Concatenate All Video Clips
            main_video = concatenate_videoclips(final_clips, method="compose")
            
            # Determine video size for intro/outro
            video_size = tuple(main_video.size) if hasattr(main_video, 'size') else (1280, 720)
            
            # 5. Add Intro and Outro Cards
            all_video_parts = []
            intro_card = None
            outro_card = None
            
            # Intro Card (configurable duration)
            if Config.INTRO_ENABLED:
                try:
                    intro_duration = Config.INTRO_DURATION
                    intro_card = self._create_intro_card(
                        house_info or {}, 
                        script_segments or [], 
                        video_size, 
                        duration=intro_duration
                    )
                    all_video_parts.append(intro_card)
                    logger.info(f"Intro card added successfully ({intro_duration}s)")
                except Exception as e:
                    logger.warning(f"Failed to add intro card: {e}")
                    intro_card = None
            
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

            # --- Subtitle Integration (P0 Feature) ---
            if script_segments and Config.SUBTITLE_ENABLED:
                try:
                    # Calculate time offset for subtitles (after intro)
                    subtitle_offset = Config.INTRO_DURATION if Config.INTRO_ENABLED else 0.0
                    
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
                    
                    # Volume control
                    bgm_clip = bgm_clip.volumex(Config.BGM_VOLUME)
                    
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
            for card in [intro_card, outro_card]:
                if card is not None:
                    try:
                        card.close()
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
