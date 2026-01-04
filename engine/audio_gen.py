import dashscope
from dashscope.audio.tts import SpeechSynthesizer
from config import Config
from html import escape as _xml_escape
import re

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
    array = getattr(audio, "array", None)
    if callable(array):
        try:
            return array()
        except Exception:
            pass
    try:
        return bytes(audio)
    except Exception:
        return None

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
                synthesizer = SpeechSynthesizerV2(
                    model=model,
                    voice=voice,
                    format=AudioFormat.MP3_48000HZ_MONO_256KBPS,
                    volume=Config.TTS_VOLUME,
                    speech_rate=Config.TTS_SPEECH_RATE,
                    pitch_rate=Config.TTS_PITCH_RATE,
                )

                ssml_or_text = _text_to_emotional_ssml(text) if Config.TTS_ENABLE_SSML else (text or "")
                try:
                    audio = synthesizer.call(ssml_or_text)
                finally:
                    try:
                        synthesizer.close()
                    except Exception:
                        pass

                audio_bytes = _bytes_from_audio(audio)
                if not audio_bytes:
                    request_id = None
                    try:
                        request_id = synthesizer.get_last_request_id()
                    except Exception:
                        pass
                    raise Exception(f"TTS failed: request_id={request_id or '-'}")

                with open(output_path, "wb") as f:
                    f.write(audio_bytes)
                return output_path

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
