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
import logging
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
import time

logger = logging.getLogger(__name__)

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
    if isinstance(audio, str):
        s = audio.strip()
        if not s:
            return None
        if s.startswith("http://") or s.startswith("https://"):
            fetched = _download_audio_url(s)
            if fetched:
                return fetched
            return None
        decoded = _maybe_decode_base64(s)
        if decoded:
            return decoded
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
    started = time.monotonic()
    host = ""
    try:
        host = urlparse(u).hostname or ""
    except Exception:
        host = ""
    try:
        with urllib.request.urlopen(u, timeout=30) as resp:
            status = getattr(resp, "status", None)
            data = resp.read()
            if data:
                return data
            logger.warning(
                "tts.audio_url.empty",
                extra={
                    "event": "tts.audio_url.empty",
                    "url_host": host,
                    "status": int(status) if status is not None else None,
                    "duration_ms": int((time.monotonic() - started) * 1000),
                },
            )
            return None
    except HTTPError as e:
        logger.warning(
            "tts.audio_url.fetch_failed",
            extra={
                "event": "tts.audio_url.fetch_failed",
                "url_host": host,
                "status": int(getattr(e, "code", 0) or 0) or None,
                "reason": (getattr(e, "reason", None) or e.__class__.__name__),
                "duration_ms": int((time.monotonic() - started) * 1000),
            },
        )
        return None
    except URLError as e:
        logger.warning(
            "tts.audio_url.fetch_failed",
            extra={
                "event": "tts.audio_url.fetch_failed",
                "url_host": host,
                "reason": (str(getattr(e, "reason", "")) or e.__class__.__name__)[:256],
                "duration_ms": int((time.monotonic() - started) * 1000),
            },
        )
        return None
    except Exception as e:
        logger.warning(
            "tts.audio_url.fetch_failed",
            extra={
                "event": "tts.audio_url.fetch_failed",
                "url_host": host,
                "reason": (str(e) or e.__class__.__name__)[:256],
                "duration_ms": int((time.monotonic() - started) * 1000),
            },
        )
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
    for p in parts:
        _assert_valid_mp3_file(p)

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
            cmd2 = [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_file,
                "-ac",
                "1",
                "-ar",
                "48000",
                "-c:a",
                "libmp3lame",
                "-q:a",
                "4",
                output_path,
            ]
            proc2 = subprocess.run(cmd2, capture_output=True, text=True)
            if proc2.returncode != 0:
                primary = (proc.stderr or proc.stdout or "").strip()
                fallback = (proc2.stderr or proc2.stdout or "").strip()
                raise RuntimeError((fallback or primary or "").strip() or "ffmpeg concat failed")
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
        if result.returncode != 0:
            return 0.0
        val = result.stdout.strip()
        return float(val) if val else 0.0
    except Exception:
        return 0.0

def _probe_audio_duration(file_path: str) -> tuple[bool, float, str]:
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            file_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            return False, 0.0, err
        out = (result.stdout or "").strip()
        if not out:
            return False, 0.0, ""
        try:
            return True, float(out), ""
        except Exception:
            return False, 0.0, out
    except Exception as e:
        return False, 0.0, (str(e) or e.__class__.__name__)

def _is_valid_mp3_file(file_path: str) -> bool:
    try:
        if not os.path.exists(file_path):
            return False
        if os.path.getsize(file_path) <= 0:
            return False
    except Exception:
        return False

    ok, duration, _err = _probe_audio_duration(file_path)
    if not ok:
        return False
    return duration > 0.01

def _assert_valid_mp3_file(file_path: str):
    try:
        size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    except Exception:
        size = -1
    ok, duration, err = _probe_audio_duration(file_path)
    if ok and duration > 0.01:
        return
    err_s = (err or "").strip()
    if len(err_s) > 800:
        err_s = err_s[:800] + "...(truncated)"
    if err_s:
        raise RuntimeError(f"invalid mp3 part: path={file_path}, size={size}, ffprobe={err_s}")
    raise RuntimeError(f"invalid mp3 part: path={file_path}, size={size}")

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
        if isinstance(obj, str) and len(obj) > 512:
            return obj[:512] + "...(truncated)"
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

def _format_exception_reason(e: Exception, limit: int = 256) -> str:
    try:
        s = str(e) or e.__class__.__name__
    except Exception:
        s = e.__class__.__name__
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\n", "\\n")
    return s[:limit]

def _parse_kv_from_reason(reason: str) -> dict:
    if not isinstance(reason, str) or not reason:
        return {}
    out = {}
    for key in ("status_code", "code", "message", "request_id"):
        if key == "message":
            m = re.search(rf"\b{re.escape(key)}=([^,;]+)", reason)
        else:
            m = re.search(rf"\b{re.escape(key)}=([^,;\s]+)", reason)
        if m:
            out[key] = m.group(1).strip()
    return out

def _classify_tts_exception(e: Exception) -> dict:
    reason = _format_exception_reason(e, limit=512)
    s = reason.lower()
    if isinstance(e, UnicodeEncodeError) or "unicodeencodeerror" in s:
        return {"tts_error_category": "invalid_text_encoding", "tts_error_detail": "unicode_encode_error"}
    if "ssml_payload_too_long" in s:
        return {"tts_error_category": "ssml_too_long", "tts_error_detail": "char_len_limit_2000"}
    if "close status: 1007" in s or "1007" in s and "close status" in s:
        return {"tts_error_category": "websocket_closed", "tts_error_detail": "close_1007"}
    if "engine return error code: 411" in s or "error code: 411" in s:
        return {"tts_error_category": "invalid_parameter", "tts_error_detail": "engine_411"}
    if "invalidparameter" in s:
        return {"tts_error_category": "invalid_parameter", "tts_error_detail": "invalidparameter"}
    if "taskfailed" in s or "task-failed" in s:
        return {"tts_error_category": "task_failed", "tts_error_detail": "task_failed"}
    if "timeout" in s or "timed out" in s:
        return {"tts_error_category": "timeout", "tts_error_detail": "timeout"}
    if "httperror" in s or "urlerror" in s:
        return {"tts_error_category": "network_error", "tts_error_detail": "http_url_error"}
    if "typeerror" in s and "enable_ssml" in s:
        return {"tts_error_category": "sdk_incompatible", "tts_error_detail": "enable_ssml_unsupported"}
    return {"tts_error_category": "unknown", "tts_error_detail": e.__class__.__name__}

def _text_to_emotional_ssml(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return "<speak></speak>"

    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    raw = re.sub(r"[\x00-\x08\x0B-\x1F\x7F]", "", raw)
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = raw.replace("……", "…").replace("......", "…").replace(".....", "…").replace("....", "…").replace("...", "…")

    raw = raw.replace("，", "，__AI_BRK_180__")
    raw = raw.replace(",", "，__AI_BRK_180__")
    raw = raw.replace("。", "。__AI_BRK_320__")
    raw = raw.replace(".", "。__AI_BRK_320__")
    raw = raw.replace("？", "？__AI_BRK_280__")
    raw = raw.replace("?", "？__AI_BRK_280__")
    raw = raw.replace("！", "！__AI_BRK_260__")
    raw = raw.replace("!", "！__AI_BRK_260__")
    raw = raw.replace("：", "：__AI_BRK_180__")
    raw = raw.replace(":", "：__AI_BRK_180__")
    raw = raw.replace("；", "；__AI_BRK_240__")
    raw = raw.replace(";", "；__AI_BRK_240__")
    raw = raw.replace("…", "__AI_BRK_650__")

    escaped = _xml_escape(raw, quote=True)
    escaped = escaped.replace("__AI_BRK_180__", "<break time=\"180ms\"/>")
    escaped = escaped.replace("__AI_BRK_320__", "<break time=\"320ms\"/>")
    escaped = escaped.replace("__AI_BRK_280__", "<break time=\"280ms\"/>")
    escaped = escaped.replace("__AI_BRK_260__", "<break time=\"260ms\"/>")
    escaped = escaped.replace("__AI_BRK_240__", "<break time=\"240ms\"/>")
    escaped = escaped.replace("__AI_BRK_650__", "<break time=\"650ms\"/>")

    return f"<speak>{escaped}</speak>"

def _is_invalid_parameter_error(err: Exception) -> bool:
    s = (str(err) or "").lower()
    return ("invalidparameter" in s) or ("engine return error code: 411" in s) or ("error code: 411" in s)

def _synthesize_text_to_mp3(
    self,
    SpeechSynthesizerV2,
    AudioFormat,
    *,
    model: str,
    voice: str,
    text: str,
    output_path: str,
    prefer_ssml: bool,
    speech_rate: float,
    asset_id: str | None,
) -> bool:
    raw_text = (text or "").strip()
    if not raw_text:
        self._generate_silence(0.2, output_path)
        return False

    if prefer_ssml:
        ssml = _text_to_emotional_ssml(raw_text)
        if _cosyvoice_char_len(ssml) <= 2000:
            self._run_tts_v2(
                SpeechSynthesizerV2,
                AudioFormat,
                model,
                voice,
                ssml,
                output_path,
                enable_ssml=True,
                speech_rate=speech_rate,
                asset_id=asset_id,
            )
            return True

    chunks = _split_text_by_limit(raw_text, 2000)
    if len(chunks) == 1:
        self._run_tts_v2(
            SpeechSynthesizerV2,
            AudioFormat,
            model,
            voice,
            chunks[0],
            output_path,
            enable_ssml=False,
            speech_rate=speech_rate,
            asset_id=asset_id,
        )
        return False

    part_files: list[str] = []
    try:
        for idx, chunk in enumerate(chunks):
            part_path = f"{output_path}.part{idx}.mp3"
            self._run_tts_v2(
                SpeechSynthesizerV2,
                AudioFormat,
                model,
                voice,
                chunk,
                part_path,
                enable_ssml=False,
                speech_rate=speech_rate,
                asset_id=asset_id,
            )
            part_files.append(part_path)
        _ffmpeg_concat_mp3(part_files, output_path)
        return False
    finally:
        for p in part_files:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

def _construct_distributed_ssml(text: str, total_silence_sec: float) -> str:
    """
    Distribute total_silence_sec among punctuations.
    """
    raw = (text or "").strip()
    if not raw:
        return f"<speak><break time=\"{int(total_silence_sec * 1000)}ms\"/></speak>"
    
    raw = raw.replace("，", "，__AI_P__")
    raw = raw.replace(",", "，__AI_P__")
    raw = raw.replace("。", "。__AI_P__")
    raw = raw.replace(".", "。__AI_P__")
    raw = raw.replace("？", "？__AI_P__")
    raw = raw.replace("?", "？__AI_P__")
    raw = raw.replace("！", "！__AI_P__")
    raw = raw.replace("!", "！__AI_P__")
    raw = raw.replace("；", "；__AI_P__")
    raw = raw.replace(";", "；__AI_P__")

    escaped = _xml_escape(raw, quote=True)
    
    # Identify slots: comma, period, question, exclamation
    puncts = ["，", "。", "？", "！", "；"]
    
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
        if p == "，": base_ms = 180
        elif p == "。": base_ms = 320
        elif p == "？": base_ms = 280
        elif p == "！": base_ms = 260
        elif p == "；": base_ms = 240
        
        final_ms = base_ms + per_slot_add_ms
        replacement = f"{p}<break time=\"{final_ms}ms\"/>"
        escaped = escaped.replace(p, replacement)

    if remaining_ms > 0:
        escaped = f"{escaped}<break time=\"{int(remaining_ms)}ms\"/>"

    escaped = escaped.replace("__AI_P__", "")
    return f"<speak>{escaped}</speak>"

def _normalize_tts_model_and_voice(*, model: str | None, voice: str | None):
    original_model = (model or "").strip()
    original_voice = (voice or "").strip()
    final_model = original_model or "cosyvoice-v3-flash"
    final_voice = original_voice or "longanyang"

    if "vc-realtime" in final_model and final_voice == "longanyang":
        fallback_model = "cosyvoice-v3-flash"
        logger.warning(
            "tts.model.voice_mismatch",
            extra={
                "event": "tts.model.voice_mismatch",
                "tts_engine": Config.TTS_ENGINE,
                "tts_model": fallback_model,
                "voice": final_voice,
                "model": final_model,
                "reason": "vc-realtime model requires cloned voice; fallback to cosyvoice-v3-flash",
            },
        )
        final_model = fallback_model

    return final_model, final_voice

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
        
        model, voice = _normalize_tts_model_and_voice(model=Config.TTS_MODEL, voice=Config.TTS_VOICE)
        
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
                
            temp_base = os.path.join(output_dir, f"{asset_id}_base.mp3")
            used_ssml = False

            try:
                try:
                    used_ssml = _synthesize_text_to_mp3(
                        self,
                        SpeechSynthesizerV2,
                        AudioFormat,
                        model=model,
                        voice=voice,
                        text=text,
                        output_path=temp_base,
                        prefer_ssml=bool(Config.TTS_ENABLE_SSML),
                        speech_rate=1.0,
                        asset_id=asset_id,
                    )
                except Exception as e:
                    err_struct = _classify_tts_exception(e)
                    logger.warning(
                        "tts.ssml.fallback",
                        extra={
                            "event": "tts.ssml.fallback",
                            "asset_id": asset_id,
                            "tts_engine": Config.TTS_ENGINE,
                            "tts_model": model,
                            "voice": voice,
                            "tts_enable_ssml": True,
                            "reason": _format_exception_reason(e, limit=256),
                            **err_struct,
                            **_parse_kv_from_reason(_format_exception_reason(e, limit=512)),
                        },
                    )
                    used_ssml = False
                    _synthesize_text_to_mp3(
                        self,
                        SpeechSynthesizerV2,
                        AudioFormat,
                        model=model,
                        voice=voice,
                        text=text,
                        output_path=temp_base,
                        prefer_ssml=False,
                        speech_rate=1.0,
                        asset_id=asset_id,
                    )

                audio_len = _get_audio_duration_sec(temp_base)
                diff = video_duration - audio_len

                if abs(diff) < 0.5:
                    os.replace(temp_base, final_path)
                elif diff > 0:
                    silence_path = os.path.join(output_dir, f"{asset_id}_pad.mp3")
                    try:
                        self._generate_silence(diff, silence_path)
                        _ffmpeg_concat_mp3([temp_base, silence_path], final_path)
                    finally:
                        if os.path.exists(temp_base):
                            try:
                                os.remove(temp_base)
                            except Exception:
                                pass
                        if os.path.exists(silence_path):
                            try:
                                os.remove(silence_path)
                            except Exception:
                                pass
                else:
                    safe_video_duration = max(video_duration, 0.1)
                    ratio = audio_len / safe_video_duration
                    target_rate = min(ratio, 1.25)
                    try:
                        _synthesize_text_to_mp3(
                            self,
                            SpeechSynthesizerV2,
                            AudioFormat,
                            model=model,
                            voice=voice,
                            text=text,
                            output_path=final_path,
                            prefer_ssml=bool(Config.TTS_ENABLE_SSML) and used_ssml,
                            speech_rate=target_rate,
                            asset_id=asset_id,
                        )
                    except Exception as e:
                        err_struct = _classify_tts_exception(e)
                        logger.warning(
                            "tts.ssml.fallback",
                            extra={
                                "event": "tts.ssml.fallback",
                                "asset_id": asset_id,
                                "tts_engine": Config.TTS_ENGINE,
                                "tts_model": model,
                                "voice": voice,
                                "tts_enable_ssml": True,
                                "reason": _format_exception_reason(e, limit=256),
                                **err_struct,
                                **_parse_kv_from_reason(_format_exception_reason(e, limit=512)),
                            },
                        )
                        _synthesize_text_to_mp3(
                            self,
                            SpeechSynthesizerV2,
                            AudioFormat,
                            model=model,
                            voice=voice,
                            text=text,
                            output_path=final_path,
                            prefer_ssml=False,
                            speech_rate=target_rate,
                            asset_id=asset_id,
                        )
                    if os.path.exists(temp_base):
                        os.remove(temp_base)
            except Exception as e:
                if os.path.exists(temp_base):
                    try:
                        os.remove(temp_base)
                    except Exception:
                        pass
                logger.exception(
                    "tts.segment.failed",
                    extra={
                        "event": "tts.segment.failed",
                        "asset_id": asset_id,
                        "tts_engine": Config.TTS_ENGINE,
                        "tts_model": model,
                        "voice": voice,
                        "tts_enable_ssml": True,
                        "reason": (str(e) or e.__class__.__name__)[:256],
                    },
                )
                raise
            
            result_map[asset_id] = final_path
            
        return result_map

    def _generate_silence(self, duration: float, output_path: str):
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=mono", 
            "-t", str(duration), "-q:a", "9", "-acodec", "libmp3lame", output_path
        ]
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if proc.returncode != 0 or not _is_valid_mp3_file(output_path):
            raise RuntimeError(f"failed to generate silence mp3: path={output_path}")

    def _run_tts_v2(self, SpeechSynthesizerV2, AudioFormat, model, voice, payload, output_path, enable_ssml=False, speech_rate=1.0, asset_id: str | None = None):
        last_audio = None
        last_request_id = None
        for attempt in range(1, 4):
            try:
                if enable_ssml and isinstance(payload, str) and _cosyvoice_char_len(payload) > 2000:
                    raise Exception("ssml_payload_too_long")
                audio, request_id = _call_tts_v2_once(
                    SpeechSynthesizerV2=SpeechSynthesizerV2,
                    AudioFormat=AudioFormat,
                    model=model,
                    voice=voice,
                    payload=payload,
                    enable_ssml=enable_ssml,
                    speech_rate=speech_rate,
                )
            except Exception as e:
                if enable_ssml and _is_invalid_parameter_error(e):
                    raise
                if attempt >= 3:
                    raise
                time.sleep(0.4 * attempt)
                continue
            last_audio = audio
            last_request_id = request_id

            status_code = getattr(audio, "status_code", None)
            if status_code is None and isinstance(audio, dict):
                status_code = audio.get("status_code")

            if status_code is not None and int(status_code) != int(HTTPStatus.OK):
                try:
                    _raise_tts_failed("TTS failed", request_id=request_id, result=audio, model=model, voice=voice)
                except Exception as e:
                    if enable_ssml and _is_invalid_parameter_error(e):
                        raise
                    raise

            audio_bytes = _bytes_from_audio(audio)
            if not audio_bytes and isinstance(audio, str):
                audio_bytes = _maybe_decode_base64(audio)

            if audio_bytes:
                with open(output_path, "wb") as f:
                    f.write(audio_bytes)
                if _is_valid_mp3_file(output_path):
                    return
                try:
                    os.remove(output_path)
                except Exception:
                    pass
                logger.warning(
                    "tts.invalid_audio",
                    extra={
                        "event": "tts.invalid_audio",
                        "attempt": int(attempt),
                        "request_id": request_id,
                        "asset_id": asset_id,
                        "output_path": output_path,
                        "payload_len": int(len(payload or "")) if isinstance(payload, str) else None,
                        "tts_engine": Config.TTS_ENGINE,
                        "tts_model": model,
                        "voice": voice,
                        "tts_enable_ssml": bool(enable_ssml),
                    },
                )
                continue

            logger.warning(
                "tts.empty_audio",
                extra={
                    "event": "tts.empty_audio",
                    "attempt": int(attempt),
                    "request_id": request_id,
                    "asset_id": asset_id,
                    "output_path": output_path,
                    "payload_len": int(len(payload or "")) if isinstance(payload, str) else None,
                    "tts_engine": Config.TTS_ENGINE,
                    "tts_model": model,
                    "voice": voice,
                    "tts_enable_ssml": bool(enable_ssml),
                },
            )
        raise Exception(
            "TTS returned empty audio: "
            f"asset_id={asset_id}; "
            f"output_path={output_path}; "
            f"request_id={last_request_id}; "
            f"result={json.dumps(_as_jsonable(last_audio), ensure_ascii=False)}"
        )

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
                model, voice = _normalize_tts_model_and_voice(model=Config.TTS_MODEL, voice=Config.TTS_VOICE)
                
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
