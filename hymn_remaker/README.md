# Hymn Remaker Pipeline

This project is an automated pipeline that takes public domain MIDI hymn files and transforms them into modern "Deep House" (or other styles) music videos for YouTube.

## Overview

The pipeline consists of the following stages:

1.  **MIDI Rendering**: Converts the input `.mid` file into a high-quality `.wav` file using FluidSynth and a SoundFont.
2.  **Music Remaking**: Uses Replicate's API (specifically Meta's `musicgen-melody`) to generate a remix conditioned on the melody of the rendered audio.
3.  **Content Generation**: Uses OpenAI's GPT-4 to generate video metadata (title, description, tags) and DALL-E 3 to generate album art.
4.  **Video Production**: Combines the remix audio and generated album art into an MP4 video using FFmpeg.
5.  **YouTube Upload**: (Optional) Uploads the generated video to YouTube using the YouTube Data API.

## Prerequisites

### System Dependencies

You need to have `fluidsynth` and `ffmpeg` installed on your system.

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y fluidsynth fluid-soundfont-gm ffmpeg
```

**macOS (Homebrew):**
```bash
brew install fluid-synth ffmpeg
```

### Python Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

### API Keys & Credentials

Create a `.env` file in the `hymn_remaker` directory (see `.env.example`) with the following keys:

-   `REPLICATE_API_TOKEN`: Your API token from [Replicate](https://replicate.com/).
-   `OPENAI_API_KEY`: Your API key from [OpenAI](https://openai.com/).
-   `ELEVENLABS_API_KEY`: (Optional) Your API key from [ElevenLabs](https://elevenlabs.io/) to generate high-quality vocals.
-   `GOOGLE_CLIENT_SECRETS_FILE`: Path to your `client_secrets.json` file for the Google/YouTube API.

**Note:** To upload to YouTube, you must create a project in the [Google Cloud Console](https://console.cloud.google.com/), enable the YouTube Data API v3, and download the OAuth 2.0 Client ID JSON file. Rename it to `client_secrets.json` and place it in the project root.

## Usage

### Docker (Recommended)

The easiest way to get the pipeline running is using Docker. This avoids needing to install system dependencies like `fluidsynth` and `ffmpeg` manually on your machine.

Make sure you have [Docker](https://docs.docker.com/get-docker/) installed, then run:

```bash
cd hymn_remaker
docker compose up --build
```

The Web UI will now be available at `http://localhost:8501`. Your `input/` and `output/` folders will be synced locally, so you can drag and drop your files or download them natively!

### Local Development / Web UI

The easiest way to use the Hymn Remaker Pipeline is through the built-in Streamlit Web UI. It allows you to upload MIDI files, tweak audio settings, and process multiple files concurrently.

```bash
python -m streamlit run hymn_remaker/app.py
```

This will launch a local web server, typically accessible at `http://localhost:8501`.

**Features in the Web UI:**
- **Concurrent Processing:** Process multiple MIDI files at the same time.
- **Style Presets:** Choose from Deep House, Lofi, Synthwave, Epic Orchestral, or write your own custom prompt.
- **Advanced Audio Processing:** Toggle volume normalization and set fade-in/fade-out durations.
- **Automatic Lyrics:** Generates synced lyric subtitles for the video.
- **TTS Vocal Generation:** Automatically detect lyrics, generate vocals using the ElevenLabs API, and mix them precisely with the remade instrumental audio track.

### Command Line Interface

You can also run the pipeline manually using the CLI by placing your MIDI files in the `hymn_remaker/input/` directory.

```bash
python3 hymn_remaker/main.py
```

### CLI Options

-   `--input-dir`: Directory containing input MIDI files (default: `hymn_remaker/input`).
-   `--output-dir`: Directory for output files (default: `hymn_remaker/output`).
-   `--soundfont`: Path to a custom SoundFont (`.sf2`) file.
-   `--style`: Musical style prompt for the remake (default: "Deep House, high quality, electronic").
-   `--upload`: Upload the generated video to YouTube.
-   `--skip-render`: Skip rendering if the base audio file already exists.
-   `--skip-remake`: Skip generation if the remake audio file already exists.

### Example (CLI)

```bash
python3 hymn_remaker/main.py --style "Lofi hip hop, chill, relaxing" --upload
```

## Structure

-   `src/midi_renderer.py`: Handles MIDI to audio conversion.
-   `src/remaker.py`: Interfaces with Replicate for music generation.
-   `src/content_generator.py`: Interfaces with OpenAI for text/image generation.
-   `src/video_uploader.py`: Handles video creation and YouTube upload.
-   `main.py`: Main orchestration script.

## License

MIT
