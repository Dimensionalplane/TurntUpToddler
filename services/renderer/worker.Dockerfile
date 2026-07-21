FROM python:3.12-slim

WORKDIR /ml-worker

# Install system deps for oemer (OpenCV/ONNX) and demucs (PyTorch)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install specific ML dependencies
RUN pip install --no-cache-dir \
    torch==2.7.1 \
    torchaudio==2.7.1 \
    oemer==0.1.8 \
    demucs==4.0.1 \
    opencv-python-headless==4.11.0.86 \
    onnxruntime==1.22.0 \
    pika \
    redis

COPY . /ml-worker/

CMD ["python", "worker.py"]
