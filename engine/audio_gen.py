import dashscope
from dashscope.audio.tts import SpeechSynthesizer
from config import Config
from html import escape as _xml_escape
from http import HTTPStatus
import re
import base64
import json
import os
import subprocess
import tempfile
import urllib.request
import math

def _format_tts_error(result) -> str:
    parts = []
    for key in ("request_id", "status_code", "code", "message"):
        value = getattr(result, key, None)
        if value is None and hasattr(result, "get"):
            try:
                value = result.get(key)
            except Exception:
                value = None
        if value not in (None, ""):
            parts.append(f"{key}={value}")
    if parts:
        return ", ".join(parts)
    try:
        return str(result)
    except Exception:
        return repr(result)

def _bytes_from_audio(audio):
    if audio is None:
        return None
    if isinstance(audio, (bytes, bytearray)):
        return bytes(audio)
    get_audio_data = getattr(audio, "get_audio_data", None)
    if callable(get_audio_data):
        try:
            data = get_audio_data()
            if data:
                return data
        except Exception:
            pass
    array = getattr(audio, "array", None)
    if callable(array):
        try:
            return array()
        except Exception:
            pass
    output = getattr(audio, "output", None)
    if output is not None:
        direct = _bytes_from_audio(output)
        if direct:
            return direct
        for key in ("audio", "audio_data", "data", "content"):
            value = getattr(output, key, None)
            direct = _bytes_from_audio(value)
            if direct:
                return direct
    if isinstance(audio, dict):
        for key in ("audio", "audio_data", "data", "content"):
            if key in audio:
                direct = _bytes_from_audio(audio.get(key))
                if direct:
                    return direct
        if "output" in audio:
            direct = _bytes_from_audio(audio.get("output"))
            if direct:
                return direct
        audio_url = audio.get("audio_url") or audio.get("url")
        if isinstance(audio_url, str):
            fetched = _download_audio_url(audio_url)
            if fetched:
                return fetched
    audio_url = getattr(audio, "audio_url", None) or getattr(audio, "url", None)
    if isinstance(audio_url, str):
        fetched = _download_audio_url(audio_url)
        if fetched:
            return fetched
    try:
        return bytes(audio)
    except Exception:
        return None

def _download_audio_url(url: str) -> bytes | None:
    u = (url or "").strip()
    if not u:
        return None
    if not (u.startswith("http://") or u.startswith("https://")):
        return None
    try:
        with urllib.request.urlopen(u, timeout=30) as resp:
            return resp.read()
    except Exception:
        return None

def _maybe_decode_base64(s: str) -> bytes | None:
    if not isinstance(s, str):
        return None
    val = s.strip()
    if not val:
        return None
    try:
        return base64.b64decode(val, validate=False)
    except Exception:
        return None

def _cosyvoice_char_len(text: str) -> int:
    s = text or ""
    if not s:
        return 0

    s = re.sub(r"<[^>]*>", "", s)

    total = 0
    for ch in s:
        o = ord(ch)
        is_han = (
            (0x3400 <= o <= 0x4DBF)
            or (0x4E00 <= o <= 0x9FFF)
            or (0xF900 <= o <= 0xFAFF)
            or (0x20000 <= o <= 0x2A6DF)
            or (0x2A700 <= o <= 0x2B73F)
            or (0x2B740 <= o <= 0x2B81F)
            or (0x2B820 <= o <= 0x2CEAF)
            or (0x2CEB0 <= o <= 0x2EBEF)
        )
        total += 2 if is_han else 1
    return total

def _split_text_by_limit(text: str, limit_chars: int) -> list[str]:
    raw = (text or "").strip()
    if not raw:
        return [""]
    if _cosyvoice_char_len(raw) <= limit_chars:
        return [raw]

    tokens = re.split(r"([。！？!?…；;，,、\n\r])", raw)
    chunks: list[str] = []
    current = ""

    def _flush():
        nonlocal current
        if current.strip():
            chunks.append(current.strip())
        current = ""

    i = 0
    while i < len(tokens):
        part = tokens[i] or ""
        punct = tokens[i + 1] if i + 1 < len(tokens) else ""
        i += 2

        segment = (part + (punct or "")).strip()
        if not segment:
            continue

        if _cosyvoice_char_len(segment) > limit_chars:
            _flush()
            for j in range(0, len(segment), 200):
                sub = segment[j : j + 200].strip()
                if sub:
                    chunks.append(sub)
            continue

        candidate = (current + segment) if current else segment
        if _cosyvoice_char_len(candidate) <= limit_chars:
            current = candidate
            continue

        _flush()
        current = segment

    _flush()
    return chunks if chunks else [raw]

def _ffmpeg_concat_mp3(parts: list[str], output_path: str):
    if len(parts) == 1:
        try:
            if parts[0] != output_path:
                with open(parts[0], "rb") as src, open(output_path, "wb") as dst:
                    dst.write(src.read())
        except Exception:
            raise
        return

    list_file = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            list_file = f.name
            for p in parts:
                safe_p = p.replace("'", "'\\''")
                f.write("file '{}'\n".format(safe_p))

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            list_file,
            "-c",
            "copy",
            output_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout or "").strip() or "ffmpeg concat failed")
    finally:
        if list_file:
            try:
                os.remove(list_file)
            except Exception:
                pass

def _get_audio_duration_sec(file_path: str) -> float:
    try:
        cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        val = result.stdout.strip()
        return float(val) if val else 0.0
    except Exception:
        return 0.0

def _call_tts_v2_once(
    *,
    SpeechSynthesizerV2,
    AudioFormat,
    model: str,
    voice: str,
    payload: str,
    enable_ssml: bool,
    speech_rate: float = 1.0,
):
    kwargs = dict(
        model=model,
        voice=voice,
        format=AudioFormat.MP3_48000HZ_MONO_256KBPS,
        volume=Config.TTS_VOLUME,
        speech_rate=speech_rate,
        pitch_rate=Config.TTS_PITCH_RATE,
    )
    if enable_ssml:
        kwargs["enable_ssml"] = True
    synthesizer = None
    try:
        try:
            synthesizer = SpeechSynthesizerV2(**kwargs)
        except TypeError:
            if "enable_ssml" in kwargs:
                kwargs.pop("enable_ssml", None)
                synthesizer = SpeechSynthesizerV2(**kwargs)
            else:
                raise

        audio = synthesizer.call(payload)
        request_id = None
        try:
            request_id = synthesizer.get_last_request_id()
        except Exception:
            pass
        return audio, request_id
    finally:
        if synthesizer is not None:
            try:
                synthesizer.close()
            except Exception:
                pass

def _as_jsonable(obj):
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (bytes, bytearray)):
        return {"type": type(obj).__name__, "len": len(obj)}
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(k, str) and k in {"api_key", "access_key", "secret", "token", "authorization"}:
                continue
            out[k] = _as_jsonable(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [_as_jsonable(v) for v in obj[:10]]
    try:
        payload = {}
        for k in ("status_code", "code", "message", "request_id", "output"):
            if hasattr(obj, k):
                payload[k] = _as_jsonable(getattr(obj, k))
        if payload:
            return payload
    except Exception:
        pass
    try:
        return str(obj)
    except Exception:
        return repr(obj)

def _raise_tts_failed(prefix: str, *, request_id: str | None, result, model: str | None, voice: str | None):
    details = _format_tts_error(result)
    meta = []
    if request_id:
        meta.append(f"request_id={request_id}")
    if model:
        meta.append(f"model={model}")
    if voice:
        meta.append(f"voice={voice}")
    if meta:
        raise Exception(f"{prefix}: {', '.join(meta)}; {details}")
    raise Exception(f"{prefix}: {details}")

def _text_to_emotional_ssml(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return "<speak></speak>"

    escaped = _xml_escape(raw, quote=True)
    escaped = escaped.replace("\r\n", "\n").replace("\r", "\n")
    escaped = re.sub(r"[ \t]+", " ", escaped)

    escaped = escaped.replace("……", "…").replace("......", "…").replace(".....", "…").replace("....", "…").replace("...", "…")

    # Standard pauses
    escaped = escaped.replace("，", "，<break time=\"180ms\"/>")
    escaped = escaped.replace(",", "，<break time=\"180ms\"/>")
    escaped = escaped.replace("。", "。<break time=\"320ms\"/>")
    escaped = escaped.replace(".", "。<break time=\"320ms\"/>")
    escaped = escaped.replace("？", "？<break time=\"280ms\"/>")
    escaped = escaped.replace("?", "？<break time=\"280ms\"/>")
    escaped = escaped.replace("！", "！<break time=\"260ms\"/>")
    escaped = escaped.replace("!", "！<break time=\"260ms\"/>")
    escaped = escaped.replace("；", "；<break time=\"240ms\"/>")
    escaped = escaped.replace(";", "；<break time=\"240ms\"/>")
    escaped = escaped.replace("：", "：<break time=\"180ms\"/>")
    escaped = escaped.replace(":", "：<break time=\"180ms\"/>")
    escaped = escaped.replace("…", "<break time=\"650ms\"/>")

    def _wrap_sentence(match: re.Match) -> str:
        content = match.group(1) or ""
        punct = match.group(2) or ""
        if punct == "！":
            return f"<prosody pitch=\"+10%\" volume=\"+2dB\">{content}{punct}</prosody>"
        if punct == "？":
            return f"<prosody pitch=\"+6%\">{content}{punct}</prosody>"
        return f"<prosody rate=\"0.98\">{content}{punct}</prosody>"

    escaped = re.sub(r"([^。！？]+)([。！？])", _wrap_sentence, escaped)

    return f"<speak>{escaped}</speak>"

def _construct_distributed_ssml(text: str, total_silence_sec: float) -> str:
    """
    Distribute total_silence_sec among punctuations.
    """
    raw = (text or "").strip()
    if not raw:
        return f"<speak><break time=\"{int(total_silence_sec * 1000)}ms\"/></speak>"
    
    escaped = _xml_escape(raw, quote=True)
    
    # Identify slots: comma, period, question, exclamation
    puncts = ["，", ",", "。", ".", "？", "?", "！", "!", "；", ";"]
    
    # Count occurrences
    count = 0
    for p in puncts:
        count += escaped.count(p)
        
    if count == 0:
        # No punctuation, append silence at end
        return f"<speak>{escaped}<break time=\"{int(total_silence_sec * 1000)}ms\"/></speak>"
    
    # Distribute
    total_ms = max(0, int(total_silence_sec * 1000))
    avg_ms = total_ms // count
    per_slot_add_ms = min(avg_ms, 800)
    remaining_ms = total_ms - (per_slot_add_ms * count)
    
    for p in puncts:
        # Base pause for this punct
        base_ms = 0
        if p in "，,": base_ms = 180
        elif p in "。.": base_ms = 320
        elif p in "？?": base_ms = 280
        elif p in "！!": base_ms = 260
        elif p in "；;": base_ms = 240
        
        final_ms = base_ms + per_slot_add_ms
        replacement = f"{p}<break time=\"{final_ms}ms\"/>"
        escaped = escaped.replace(p, replacement)

    if remaining_ms > 0:
        escaped = f"{escaped}<break time=\"{int(remaining_ms)}ms\"/>"

    return f"<speak>{escaped}</speak>"

class AudioGenerator:
    def __init__(self):
        if not Config.DASHSCOPE_API_KEY:
            raise ValueError("DASHSCOPE_API_KEY is not set")
        dashscope.api_key = Config.DASHSCOPE_API_KEY
        
    def generate_audio(self, text: str, output_path: str):
        """
        Legacy single-file generation (still used for test or simple cases)
        """
        return self._generate_internal(text, output_path)

    def generate_aligned_audio_segments(self, segments: list, output_dir: str) -> dict:
        """
        Generate audio segments aligned with video duration.
        segments: list of dict, each containing 'text', 'duration', 'asset_id'
        Returns: dict mapping asset_id to audio_file_path
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        result_map = {}
        
        # Pre-check engine support
        use_v2 = Config.TTS_ENGINE in {"cosyvoice", "tts_v2"}
        if not use_v2:
            # Fallback for legacy engine (no SSML/Speed control)
            for seg in segments:
                aid = seg.get('asset_id')
                txt = seg.get('text')
                path = os.path.join(output_dir, f"{aid}.mp3")
                self._generate_internal(txt, path)
                result_map[aid] = path
            return result_map

        # Use TTS V2
        from dashscope.audio.tts_v2 import SpeechSynthesizer as SpeechSynthesizerV2
        from dashscope.audio.tts_v2.speech_synthesizer import AudioFormat
        
        model = Config.TTS_MODEL or "cosyvoice-v3-flash"
        voice = Config.TTS_VOICE or "longanyang"
        
        for seg in segments:
            text = seg.get('text', '').strip()
            video_duration = float(seg.get('duration', 5.0))
            asset_id = seg.get('asset_id')
            if not asset_id: 
                continue
                
            final_path = os.path.join(output_dir, f"{asset_id}.mp3")
            
            if not text:
                # Generate silence
                self._generate_silence(video_duration, final_path)
                result_map[asset_id] = final_path
                continue
                
            # 1. Generate Baseline (Standard Rate, Emotional SSML)
            # Use temp file
            temp_base = os.path.join(output_dir, f"{asset_id}_base.mp3")
            
            # Use standard emotional SSML for baseline
            baseline_ssml = _text_to_emotional_ssml(text)
            
            self._run_tts_v2(
                SpeechSynthesizerV2, AudioFormat, 
                model, voice, baseline_ssml, temp_base, 
                enable_ssml=True, speech_rate=1.0
            )
            
            audio_len = _get_audio_duration_sec(temp_base)
            diff = video_duration - audio_len
            
            # Threshold 0.5s
            if abs(diff) < 0.5:
                # Accept baseline
                os.replace(temp_base, final_path)
                
            elif diff > 0:
                # Video > Audio: Insert Silence
                # Use distributed SSML
                dist_ssml = _construct_distributed_ssml(text, diff)
                self._run_tts_v2(
                    SpeechSynthesizerV2, AudioFormat,
                    model, voice, dist_ssml, final_path,
                    enable_ssml=True, speech_rate=1.0
                )
                if os.path.exists(temp_base):
                    os.remove(temp_base)
                    
            else:
                # Video < Audio: Speed Up
                # ratio = audio / video
                safe_video_duration = max(video_duration, 0.1)
                ratio = audio_len / safe_video_duration
                
                # Limit max speed to 1.25
                target_rate = min(ratio, 1.25)
                
                # If ratio is very small (e.g. 1.05), just speed up.
                # If ratio is huge (e.g. 2.0), we cap at 1.25, and video will have to loop/slow-mo.
                
                # Generate with speed up
                # Note: When speeding up, we should use raw text or minimal SSML to avoid double pauses?
                # But we still want emotional prosody.
                # Let's use the same emotional SSML but with higher global rate.
                
                self._run_tts_v2(
                    SpeechSynthesizerV2, AudioFormat,
                    model, voice, baseline_ssml, final_path,
                    enable_ssml=True, speech_rate=target_rate
                )
                if os.path.exists(temp_base):
                    os.remove(temp_base)
            
            result_map[asset_id] = final_path
            
        return result_map

    def _generate_silence(self, duration: float, output_path: str):
        # Generate silence mp3 using ffmpeg
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=mono", 
            "-t", str(duration), "-q:a", "9", "-acodec", "libmp3lame", output_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _run_tts_v2(self, SpeechSynthesizerV2, AudioFormat, model, voice, payload, output_path, enable_ssml=False, speech_rate=1.0):
        audio, request_id = _call_tts_v2_once(
            SpeechSynthesizerV2=SpeechSynthesizerV2,
            AudioFormat=AudioFormat,
            model=model,
            voice=voice,
            payload=payload,
            enable_ssml=enable_ssml,
            speech_rate=speech_rate
        )
        
        status_code = getattr(audio, "status_code", None)
        if status_code is None and isinstance(audio, dict):
            status_code = audio.get("status_code")
            
        if status_code is not None and int(status_code) != int(HTTPStatus.OK):
            _raise_tts_failed("TTS failed", request_id=request_id, result=audio, model=model, voice=voice)
            
        audio_bytes = _bytes_from_audio(audio)
        if not audio_bytes and isinstance(audio, str):
            audio_bytes = _maybe_decode_base64(audio)
            
        if audio_bytes:
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
        else:
            raise Exception(f"TTS returned empty audio: request_id={request_id}")

    def _generate_internal(self, text, output_path):
        # Legacy support logic...
        # Copied from original generate_audio logic
        if Config.TTS_ENGINE in {"cosyvoice", "tts_v2"}:
            try:
                from dashscope.audio.tts_v2 import SpeechSynthesizer as SpeechSynthesizerV2
                from dashscope.audio.tts_v2.speech_synthesizer import AudioFormat
            except Exception:
                pass
            else:
                # Use simple V2 call
                model = Config.TTS_MODEL or "cosyvoice-v3-flash"
                voice = Config.TTS_VOICE or "longanyang"
                
                chunks = _split_text_by_limit(text or "", 2000)
                part_files = []
                try:
                    for idx, chunk in enumerate(chunks):
                        p_path = f"{output_path}.part{idx}.mp3"
                        ssml = _text_to_emotional_ssml(chunk) if Config.TTS_ENABLE_SSML else chunk
                        self._run_tts_v2(
                            SpeechSynthesizerV2, AudioFormat, model, voice, 
                            ssml, p_path, enable_ssml=Config.TTS_ENABLE_SSML
                        )
                        part_files.append(p_path)
                    
                    if len(part_files) == 1:
                        os.rename(part_files[0], output_path)
                    else:
                        _ffmpeg_concat_mp3(part_files, output_path)
                    return output_path
                finally:
                    for p in part_files:
                        if os.path.exists(p): os.remove(p)
                        
        # Fallback to V1
        result = SpeechSynthesizer.call(
            model="sambert-zh-CN-v1",
            text=(text or ""),
            sample_rate=48000,
            format="mp3",
        )
        if result.get_audio_data() is not None:
            with open(output_path, 'wb') as f:
                f.write(result.get_audio_data())
            return output_path
        else:
            raise Exception(f"TTS failed: {_format_tts_error(result)}")
