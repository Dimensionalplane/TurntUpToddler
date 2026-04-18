# Deployment Instructions

## System Requirements
- Python 3.10+
- `ffmpeg`
- `fluidsynth` and a valid soundfont (e.g., `fluid-soundfont-gm`)
- Docker (optional, for containerized deployment)

## Local Setup
1. Clone the repository.
2. Install system dependencies:
   ```bash
   sudo apt-get update && sudo apt-get install -y ffmpeg fluidsynth fluid-soundfont-gm libfluidsynth-dev
   ```
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set required environment variables:
   - `OPENAI_API_KEY`
   - `REPLICATE_API_TOKEN`
   - `ELEVENLABS_API_KEY`

## Running the Pipeline
- **CLI**: `python -m hymn_remaker.main --input input/my_hymn.mid`
- **Daemon Mode**: `python -m hymn_remaker.main --daemon`
- **Web UI**: `python -m streamlit run hymn_remaker/app.py`

## Docker Deployment
1. Build the image:
   ```bash
   docker build -t hymn_remaker .
   ```
2. Run via Compose:
   ```bash
   docker-compose up -d
   ```
