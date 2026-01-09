import os
import logging
from typing import Optional
from config import Config

logger = logging.getLogger(__name__)

class SFXLibrary:
    """
    Sound Effects Library Manager
    Maps audio_cue strings to actual sound effect files
    """
    
    def __init__(self, library_path: str = None):
        self.library_path = library_path or Config.SFX_LIBRARY_PATH
        
        # Mapping: normalized_cue -> filename
        # These are common SFX for real estate videos
        self.sfx_mapping = {
            # Nature sounds
            "birds_chirping": "birds.mp3",
            "birds": "birds.mp3",
            "bird_sound": "birds.mp3",
            "soft_wind": "wind.mp3",
            "wind": "wind.mp3",
            "gentle_breeze": "wind.mp3",
            
            # Interior sounds
            "door_open": "door_open.mp3",
            "door_close": "door_close.mp3",
            "footsteps": "footsteps.mp3",
            "footsteps_on_wood": "footsteps_wood.mp3",
            "window_open": "window.mp3",
            
            # Ambient sounds
            "morning_jazz": "jazz_light.mp3",
            "soft_morning_jazz_music": "jazz_light.mp3",
            "acoustic_guitar": "guitar_ambient.mp3",
            "water_flowing": "water.mp3",
            
            # Transition sounds
            "whoosh": "whoosh.mp3",
            "subtle_transition": "transition.mp3",
        }
    
    def normalize_cue(self, cue: str) -> str:
        """Normalize audio_cue to lowercase with underscores"""
        if not cue:
            return ""
        return cue.lower().strip().replace(" ", "_").replace("-", "_")
    
    def get_sfx_path(self, audio_cue: str) -> Optional[str]:
        """
        Get full path to SFX file based on audio_cue.
        Returns None if not found or file doesn't exist.
        """
        if not audio_cue or not Config.SFX_ENABLED:
            return None
        
        normalized = self.normalize_cue(audio_cue)
        
        # Try direct mapping
        filename = self.sfx_mapping.get(normalized)
        
        if not filename:
            # Try partial match (e.g., "birds chirping softly" -> "birds")
            for key in self.sfx_mapping.keys():
                if key in normalized or normalized in key:
                    filename = self.sfx_mapping[key]
                    break
        
        if not filename:
            logger.debug(f"No SFX mapping found for: {audio_cue}")
            return None
        
        # Build full path
        full_path = os.path.join(self.library_path, filename)
        
        if not os.path.exists(full_path):
            logger.warning(f"SFX file not found: {full_path}")
            return None
        
        logger.debug(f"SFX resolved: '{audio_cue}' -> {full_path}")
        return full_path
    
    def is_available(self) -> bool:
        """Check if SFX library is properly configured"""
        return (
            Config.SFX_ENABLED 
            and os.path.exists(self.library_path) 
            and os.path.isdir(self.library_path)
        )
    
    def list_available_sfx(self) -> list[str]:
        """List all available SFX files in the library"""
        if not os.path.exists(self.library_path):
            return []
        
        try:
            files = os.listdir(self.library_path)
            return [f for f in files if f.endswith(('.mp3', '.wav', '.ogg'))]
        except Exception as e:
            logger.error(f"Failed to list SFX library: {e}")
            return []
