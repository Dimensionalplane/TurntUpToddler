FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY hymn_remaker/requirements.txt .
RUN pip install --no-cache-dir \
    redis==5.0.3 \
    pika==1.3.2 \
    python-dotenv==1.1.1

# Copy the application code
COPY . .

# Start the radio worker
CMD ["python", "services/radio/worker.py"]
