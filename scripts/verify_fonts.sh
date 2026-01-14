#!/bin/bash
# Font Verification Script
# Usage: ./scripts/verify_fonts.sh [container_name]

set -e

CONTAINER_NAME="${1:-ai-scene-engine}"

echo "=== Font Verification Tool ==="
echo "Container: $CONTAINER_NAME"
echo ""

# Check if container is running
if ! docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Container '$CONTAINER_NAME' is not running"
    echo "Available containers:"
    docker ps --format "  - {{.Names}}"
    exit 1
fi

echo "✓ Container is running"
echo ""

# Check custom fonts directory
echo "📁 Checking custom fonts directory..."
docker exec "$CONTAINER_NAME" bash -c "
    if [ -d /app/assets/fonts ]; then
        echo '✓ /app/assets/fonts exists'
        echo 'Font files:'
        ls -lh /app/assets/fonts/ | grep -E '\.(ttf|otf)$' | awk '{print \"  -\", \$9, \"(\"\$5\")\"}'
    else
        echo '❌ /app/assets/fonts not found'
    fi
"
echo ""

# Check system fonts directory
echo "📁 Checking system fonts directory..."
docker exec "$CONTAINER_NAME" bash -c "
    if [ -d /usr/share/fonts/truetype/custom ]; then
        echo '✓ /usr/share/fonts/truetype/custom exists'
        echo 'Registered fonts:'
        ls -lh /usr/share/fonts/truetype/custom/ | grep -E '\.(ttf|otf)$' | awk '{print \"  -\", \$9, \"(\"\$5\")\"}'
    else
        echo '❌ /usr/share/fonts/truetype/custom not found'
    fi
"
echo ""

# List all available fonts
echo "🔍 Searching for custom fonts in fc-list..."
docker exec "$CONTAINER_NAME" bash -c "
    fc-list | grep -i 'alibaba\|puhuiti' || echo '❌ No Alibaba PuHuiTi fonts found'
"
echo ""

# Test font with Python
echo "🐍 Testing font with Python FontManager..."
docker exec "$CONTAINER_NAME" python3 -c "
from font_manager import FontManager
from config import Config

# Print configured font
print(f'Configured font: {Config.SUBTITLE_FONT}')
print(f'Font key: {Config._FONT_KEY}')
print('')

# Validate configured font
is_valid = FontManager.validate_font(Config.SUBTITLE_FONT)
print(f'Font validation: {\"✓ Available\" if is_valid else \"❌ Not Found\"}')
print('')

# Search for custom fonts
custom_fonts = FontManager.search_font('alibaba')
if custom_fonts:
    print(f'Found {len(custom_fonts)} Alibaba fonts:')
    for font in custom_fonts:
        print(f'  - {font}')
else:
    print('❌ No Alibaba fonts found')
"
echo ""

# Test subtitle rendering (requires moviepy)
echo "🎬 Testing subtitle rendering..."
docker exec "$CONTAINER_NAME" python3 -c "
from moviepy.editor import TextClip
from config import Config
import tempfile
import os

try:
    # Create a simple test subtitle
    test_text = '测试字幕 Test Subtitle'
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'test_subtitle.png')
        
        txt_clip = TextClip(
            test_text,
            fontsize=48,
            color='white',
            font=Config.SUBTITLE_FONT,
            stroke_color='black',
            stroke_width=2,
            method='caption',
            size=(800, None),
            align='center'
        )
        
        # Save frame to test rendering
        txt_clip.save_frame(output_path, t=0)
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f'✓ Subtitle rendering successful')
            print(f'  Text: {test_text}')
            print(f'  Font: {Config.SUBTITLE_FONT}')
            print(f'  Output: {file_size} bytes')
        else:
            print('❌ Subtitle rendering failed: output file not created')
            
except Exception as e:
    print(f'❌ Subtitle rendering failed: {e}')
" || echo "⚠️ Subtitle rendering test failed (this is normal if MoviePy is not configured)"
echo ""

# Summary
echo "=== Verification Complete ==="
echo "Next steps:"
echo "  1. If fonts are not found, rebuild the Docker image"
echo "  2. If rendering fails, check ImageMagick configuration"
echo "  3. View full font status in container logs"
