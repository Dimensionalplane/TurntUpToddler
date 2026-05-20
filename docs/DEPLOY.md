# Deployment Guide

The standard deployment method is via Docker.

## Prerequisites
- Docker & Docker Compose
- `.env` file populated with `OPENAI_API_KEY`, `REPLICATE_API_TOKEN`, `ELEVENLABS_API_KEY`, and `GOOGLE_CLIENT_SECRETS_FILE`.

## Build and Run
```bash
cd hymn_remaker
docker compose build
docker compose up -d
```

## Updating (via version control)
Update your local repository, then run:
```bash
docker compose up -d --build
```
# Deployment Instructions

This document provides comprehensive instructions for deploying the Hymn Remaker pipeline across various environments.

## System Prerequisites
Before installing Python dependencies, ensure the host system has the necessary native multimedia libraries.

### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg fluidsynth fluid-soundfont-gm libfluidsynth-dev build-essential rubberband-cli
```

### macOS (Homebrew)
```bash
brew install ffmpeg fluidsynth rubberband
```

## Local Python Environment Setup
1. **Clone the repository:**
   ```bash
   git clone https://github.com/robertpelloni/hymnmania.git
   cd hymnmania
   ```
2. **Create a virtual environment (Recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Compiling the C++ Engine (Optional)
To run tests or utilize the native C++ `HymnPlayer` wrapper:
```bash
make clean && make
./tests/run_tests
```

## API Key Configuration
The pipeline relies heavily on third-party APIs. You must set the following environment variables (or place them in a `.env` file if supported by the environment):
- `OPENAI_API_KEY`: Required for metadata, lyrics, and DALL-E 3 cover art generation.
- `REPLICATE_API_TOKEN`: Required for the MusicGen audio-to-audio Deep House remixing.
- `ELEVENLABS_API_KEY`: Required for TTS vocal track generation.
- `client_secrets.json`: If utilizing the automated YouTube upload feature, this OAuth2 credentials file must be present in the project root.

## Running the Application

### 1. Command Line Interface (CLI)
Process a single MIDI file manually:
```bash
python -m hymn_remaker.main --input input/my_hymn.mid --video-format "Vertical 9:16" --create-shorts
```

### 2. Daemon Mode
Run the application continuously. It will monitor the `input/` directory using `watchdog` and automatically process any newly added `.mid` files.
```bash
python -m hymn_remaker.main --daemon
```

### 3. Streamlit Web UI
Launch the interactive dashboard for real-time monitoring and parameter configuration:
```bash
python -m streamlit run hymn_remaker/app.py
```

## Docker Containerization
For isolated, consistent deployments, a Docker setup is provided.

1. **Build the image:**
   ```bash
   docker build -t hymn_remaker:latest .
   ```
2. **Run via Docker Compose:**
   Ensure your API keys are defined in the environment or a `.env` file before running.
   ```bash
   docker-compose up -d
   ```