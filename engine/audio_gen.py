import dashscope
from dashscope.audio.tts import SpeechSynthesizer
from config import Config
import os

class AudioGenerator:
    def __init__(self):
        if not Config.DASHSCOPE_API_KEY:
            raise ValueError("DASHSCOPE_API_KEY is not set")
        
    def generate_audio(self, text: str, output_path: str):
        """
        Convert text to speech using DashScope Sambert model.
        """
        # Sambert-zh-CN-v1 is a standard voice model
        result = SpeechSynthesizer.call(model='sambert-zh-CN-v1',
                                      text=text,
                                      sample_rate=48000,
                                      format='mp3')

        if result.get_audio_data() is not None:
            with open(output_path, 'wb') as f:
                f.write(result.get_audio_data())
            return output_path
        else:
            raise Exception(f"TTS failed: {result.message}")
