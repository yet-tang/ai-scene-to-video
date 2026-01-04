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

def _call_tts_v2_once(
    *,
    SpeechSynthesizerV2,
    AudioFormat,
    model: str,
    voice: str,
    payload: str,
    enable_ssml: bool,
):
    kwargs = dict(
        model=model,
        voice=voice,
        format=AudioFormat.MP3_48000HZ_MONO_256KBPS,
        volume=Config.TTS_VOLUME,
        speech_rate=Config.TTS_SPEECH_RATE,
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

class AudioGenerator:
    def __init__(self):
        if not Config.DASHSCOPE_API_KEY:
            raise ValueError("DASHSCOPE_API_KEY is not set")
        dashscope.api_key = Config.DASHSCOPE_API_KEY
        
    def generate_audio(self, text: str, output_path: str):
        """
        Convert text to speech.
        """
        if Config.TTS_ENGINE in {"cosyvoice", "tts_v2"}:
            try:
                from dashscope.audio.tts_v2 import SpeechSynthesizer as SpeechSynthesizerV2
                from dashscope.audio.tts_v2.speech_synthesizer import AudioFormat
            except Exception:
                SpeechSynthesizerV2 = None
                AudioFormat = None

            if SpeechSynthesizerV2 and AudioFormat:
                model = Config.TTS_MODEL or "cosyvoice-v3-flash"
                voice = Config.TTS_VOICE or "longanyang"

                chunks = _split_text_by_limit(text or "", 2000)
                part_files: list[str] = []
                try:
                    for idx, chunk in enumerate(chunks):
                        attempts = []
                        if Config.TTS_ENABLE_SSML:
                            attempts.append(("ssml", _text_to_emotional_ssml(chunk), True))
                        attempts.append(("text", chunk, False))

                        last_result = None
                        last_request_id = None
                        for mode, payload, enable_ssml in attempts:
                            audio, request_id = _call_tts_v2_once(
                                SpeechSynthesizerV2=SpeechSynthesizerV2,
                                AudioFormat=AudioFormat,
                                model=model,
                                voice=voice,
                                payload=payload,
                                enable_ssml=enable_ssml,
                            )
                            last_result = audio
                            last_request_id = request_id

                            status_code = getattr(audio, "status_code", None)
                            if status_code is None and isinstance(audio, dict):
                                status_code = audio.get("status_code")
                            if status_code is not None and int(status_code) != int(HTTPStatus.OK):
                                if mode == attempts[-1][0]:
                                    _raise_tts_failed(
                                        "TTS request failed",
                                        request_id=last_request_id,
                                        result=audio,
                                        model=model,
                                        voice=voice,
                                    )
                                continue

                            audio_bytes = _bytes_from_audio(audio)
                            if not audio_bytes and isinstance(audio, str):
                                audio_bytes = _maybe_decode_base64(audio)
                            if audio_bytes:
                                if len(chunks) == 1:
                                    with open(output_path, "wb") as f:
                                        f.write(audio_bytes)
                                    return output_path
                                part_path = f"{output_path}.part{idx:04d}.mp3"
                                with open(part_path, "wb") as f:
                                    f.write(audio_bytes)
                                part_files.append(part_path)
                                break

                            if mode == attempts[-1][0]:
                                raise Exception(
                                    f"TTS returned empty audio: request_id={last_request_id or '-'}; result={json.dumps(_as_jsonable(last_result), ensure_ascii=False)}"
                                )

                    if len(chunks) > 1:
                        _ffmpeg_concat_mp3(part_files, output_path)
                        return output_path
                finally:
                    for p in part_files:
                        try:
                            os.remove(p)
                        except Exception:
                            pass

        result = SpeechSynthesizer.call(
            model=((Config.TTS_MODEL or "sambert-zh-CN-v1") if Config.TTS_ENGINE not in {"cosyvoice", "tts_v2"} else "sambert-zh-CN-v1"),
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
