FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for OpenCV and FFmpeg
# libgl1-mesa-glx is not needed for opencv-python-headless and causes issues on Debian Bookworm
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Start Celery Worker
CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info"]
