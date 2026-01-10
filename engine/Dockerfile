FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for OpenCV, FFmpeg, ImageMagick, and fonts
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    ffmpeg \
    imagemagick \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Configure ImageMagick security policy for MoviePy TextClip rendering
# - Allow reading from temporary files (@ prefix for text input)
# - Allow PDF/text operations
# - Remove restrictive policies that block subtitle generation
RUN if [ -f /etc/ImageMagick-6/policy.xml ]; then \
        sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml; \
        sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@*"/' /etc/ImageMagick-6/policy.xml; \
        sed -i '/<policy domain="path" rights="none" pattern="@\*"/d' /etc/ImageMagick-6/policy.xml; \
        sed -i '/<policy domain="coder" rights="none" pattern="TEXT"/d' /etc/ImageMagick-6/policy.xml; \
        sed -i '/<policy domain="coder" rights="none" pattern="LABEL"/d' /etc/ImageMagick-6/policy.xml; \
    fi

# Regenerate font cache for MoviePy/ImageMagick
RUN fc-cache -f -v || true

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Start Celery Worker
# Concurrency can be controlled via CELERY_WORKER_CONCURRENCY env var (default: 2 for 4GB VPS)
# Use shell form to allow environment variable expansion
CMD celery -A worker.celery_app worker --loglevel=info --concurrency=${CELERY_WORKER_CONCURRENCY:-2}
