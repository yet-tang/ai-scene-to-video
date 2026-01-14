"""
Font Management Module

Provides utilities for managing and validating fonts in the video rendering pipeline.
Supports both system fonts and custom fonts from /app/assets/fonts.
"""

import subprocess
import os
import logging
from typing import List, Dict, Optional

from config import Config

logger = logging.getLogger(__name__)


class FontManager:
    """Manages font discovery, validation, and registration"""
    
    CUSTOM_FONT_DIR = "/app/assets/fonts"
    SYSTEM_FONT_DIR = "/usr/share/fonts/truetype/custom"
    
    @staticmethod
    def list_available_fonts() -> List[str]:
        """
        List all available fonts in the system using fc-list.
        
        Returns:
            List of font family names
        """
        try:
            result = subprocess.run(
                ['fc-list', ':', 'family'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse fc-list output (format: "Font Family,Alternative Name")
                fonts = set()
                for line in result.stdout.splitlines():
                    # Split by comma and take all variations
                    for font_name in line.split(','):
                        font_name = font_name.strip()
                        if font_name:
                            fonts.add(font_name)
                return sorted(list(fonts))
            else:
                logger.warning(f"fc-list failed: {result.stderr}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to list fonts: {e}")
            return []
    
    @staticmethod
    def search_font(pattern: str) -> List[str]:
        """
        Search for fonts matching a pattern.
        
        Args:
            pattern: Search pattern (case-insensitive)
            
        Returns:
            List of matching font names
        """
        all_fonts = FontManager.list_available_fonts()
        pattern_lower = pattern.lower()
        return [f for f in all_fonts if pattern_lower in f.lower()]
    
    @staticmethod
    def validate_font(font_name: str) -> bool:
        """
        Check if a font is available in the system.
        
        Args:
            font_name: Font family name to check
            
        Returns:
            True if font is available, False otherwise
        """
        try:
            result = subprocess.run(
                ['fc-list', ':', 'family'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Check if font name appears in output (case-insensitive)
                font_name_lower = font_name.lower()
                for line in result.stdout.splitlines():
                    if font_name_lower in line.lower():
                        return True
                        
            return False
            
        except Exception as e:
            logger.error(f"Failed to validate font '{font_name}': {e}")
            return False
    
    @staticmethod
    def list_custom_fonts() -> Dict[str, str]:
        """
        List custom font files in the custom font directory.
        
        Returns:
            Dict mapping filename to full path
        """
        custom_fonts = {}
        
        if os.path.exists(FontManager.CUSTOM_FONT_DIR):
            for filename in os.listdir(FontManager.CUSTOM_FONT_DIR):
                if filename.endswith(('.ttf', '.otf', '.TTF', '.OTF')):
                    full_path = os.path.join(FontManager.CUSTOM_FONT_DIR, filename)
                    custom_fonts[filename] = full_path
        
        return custom_fonts
    
    @staticmethod
    def get_font_info(font_name: str) -> Optional[Dict[str, str]]:
        """
        Get detailed information about a font.
        
        Args:
            font_name: Font family name
            
        Returns:
            Dict with font info (family, style, file) or None if not found
        """
        try:
            result = subprocess.run(
                ['fc-list', font_name, 'family', 'style', 'file'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # Parse output (format: "/path/to/font.ttf: Font Family:style=Style Name")
                line = result.stdout.splitlines()[0]
                parts = line.split(':')
                
                if len(parts) >= 2:
                    return {
                        'file': parts[0].strip(),
                        'family': parts[1].strip() if len(parts) > 1 else '',
                        'style': parts[2].strip() if len(parts) > 2 else ''
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get font info for '{font_name}': {e}")
            return None
    
    @staticmethod
    def register_custom_fonts() -> int:
        """
        Register all custom fonts from CUSTOM_FONT_DIR.
        Should be called after copying fonts to SYSTEM_FONT_DIR.
        
        Returns:
            Number of fonts registered
        """
        try:
            # Run fc-cache to rebuild font cache
            result = subprocess.run(
                ['fc-cache', '-f', '-v'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("Font cache rebuilt successfully")
                
                # Count registered custom fonts
                custom_fonts = FontManager.list_custom_fonts()
                logger.info(f"Registered {len(custom_fonts)} custom fonts: {list(custom_fonts.keys())}")
                
                return len(custom_fonts)
            else:
                logger.warning(f"fc-cache failed: {result.stderr}")
                return 0
                
        except Exception as e:
            logger.error(f"Failed to register custom fonts: {e}")
            return 0
    
    @staticmethod
    def log_font_status():
        """
        Log comprehensive font status information for debugging.
        """
        logger.info("=== Font Manager Status ===")
        
        # Custom fonts directory
        custom_fonts = FontManager.list_custom_fonts()
        logger.info(f"Custom fonts directory: {FontManager.CUSTOM_FONT_DIR}")
        logger.info(f"Custom font files found: {len(custom_fonts)}")
        for filename, path in custom_fonts.items():
            logger.info(f"  - {filename} -> {path}")
        
        # Available fonts
        available_fonts = FontManager.list_available_fonts()
        logger.info(f"Total system fonts available: {len(available_fonts)}")
        
        # Check specific fonts
        configured_font = Config.SUBTITLE_FONT
        is_available = FontManager.validate_font(configured_font)
        logger.info(f"Configured font '{configured_font}': {'✓ Available' if is_available else '✗ Not Found'}")
        
        # Search for Chinese fonts
        chinese_fonts = FontManager.search_font('CJK')
        logger.info(f"Chinese (CJK) fonts found: {len(chinese_fonts)}")
        for font in chinese_fonts[:5]:  # Show first 5
            logger.info(f"  - {font}")
        
        logger.info("=========================")


# Convenience function for quick font check
def quick_font_check(font_name: str) -> bool:
    """
    Quick check if a font is available.
    
    Args:
        font_name: Font name to check
        
    Returns:
        True if available, False otherwise
    """
    return FontManager.validate_font(font_name)
