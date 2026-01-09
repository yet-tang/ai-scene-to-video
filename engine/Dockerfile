FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for OpenCV, FFmpeg, and ImageMagick
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    ffmpeg \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

# Configure ImageMagick to allow PDF/text operations
# MoviePy requires ImageMagick for TextClip rendering
RUN sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml || true

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Start Celery Worker
CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info"]
