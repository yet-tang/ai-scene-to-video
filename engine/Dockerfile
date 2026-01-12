FROM python:3.10-slim

WORKDIR /app

ARG IMAGE_TAG=unknown
ARG GIT_COMMIT=unknown
ARG BUILD_TIME

# Set version info as environment variables
ENV IMAGE_TAG=$IMAGE_TAG
ENV GIT_COMMIT=$GIT_COMMIT
ENV BUILD_TIME=$BUILD_TIME

# Install system dependencies for OpenCV, FFmpeg, ImageMagick, and fonts
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    ffmpeg \
    imagemagick \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Configure ImageMagick security policy for MoviePy TextClip rendering
# Support both ImageMagick-6 and ImageMagick-7
# - Allow reading from temporary files (@ prefix for text input)
# - Allow PDF/text/label operations
# - Remove restrictive policies that block subtitle generation
RUN for policy_file in /etc/ImageMagick-*/policy.xml; do \
        if [ -f "$policy_file" ]; then \
            echo "Configuring ImageMagick policy: $policy_file"; \
            # Remove restrictive path policy for @ (text input)
            sed -i '/<policy domain="path" rights="none" pattern="@\*"/d' "$policy_file"; \
            # Allow read|write for @ pattern if exists, or just remove the restriction
            sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@*"/g' "$policy_file"; \
            # Allow PDF operations
            sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/g' "$policy_file"; \
            # Remove TEXT/LABEL coder restrictions
            sed -i '/<policy domain="coder" rights="none" pattern="TEXT"/d' "$policy_file"; \
            sed -i '/<policy domain="coder" rights="none" pattern="LABEL"/d' "$policy_file"; \
            # Add explicit allow policy for TEXT if not exists
            grep -q 'pattern="TEXT"' "$policy_file" || \
                sed -i '/<policymap>/a \  <policy domain="coder" rights="read|write" pattern="TEXT" />' "$policy_file"; \
            grep -q 'pattern="LABEL"' "$policy_file" || \
                sed -i '/<policymap>/a \  <policy domain="coder" rights="read|write" pattern="LABEL" />' "$policy_file"; \
        fi; \
    done

# Regenerate font cache for MoviePy/ImageMagick
RUN fc-cache -f -v || true

# Verify ImageMagick and font setup
RUN convert -list font | head -20 || echo "Font listing not available"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Print version info at startup
RUN echo "=== Engine Build Info ===" && \
    echo "IMAGE_TAG: $IMAGE_TAG" && \
    echo "GIT_COMMIT: $GIT_COMMIT" && \
    echo "BUILD_TIME: $BUILD_TIME" && \
    echo "========================="

# Start Celery Worker
# Concurrency can be controlled via CELERY_WORKER_CONCURRENCY env var (default: 2 for 4GB VPS)
# Use shell form to allow environment variable expansion
CMD celery -A worker.celery_app worker --loglevel=info --concurrency=${CELERY_WORKER_CONCURRENCY:-2}
