FROM python:3.12-alpine

WORKDIR /app

# Install runtime system dependencies for rendering
RUN apk add --no-cache \
    ffmpeg \
    fluidsynth \
    fluid-soundfont-gm \
    libstdc++ \
    build-base

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the renderer service
COPY renderer.py .

CMD ["python", "renderer.py"]
