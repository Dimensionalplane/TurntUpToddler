# HANDOFF.md: Project Architecture, History, and Next Steps
**Version:** 1.2.0
**Date:** 2024-05-22

## Overview & State
The `hymn_remaker` project is an incredibly robust, automated AI pipeline for transforming public domain `.mid` files into modern, YouTube-ready music videos. It features parallel processing, Web UI, dynamic audio processing, and professional AI integrations (OpenAI, Replicate, ElevenLabs).

The codebase is highly functional, 100% stable, strictly typed, and completely modular.

## Core Features Implemented
1. **Web UI (`app.py`)**: Built with Streamlit (`port 8501`). Features two main tabs:
   - **Generate**: Handles multiple `.mid` file uploads. Validates the `MThd` MIDI byte signature instantly. Exposes sliders for Concurrency limits, Dropdowns for Style Presets, an expander for Audio Fading/Normalization, a checkbox to generate ElevenLabs Vocals, and a checkbox to use a dynamic FFmpeg visualizer over static DALL-E art.
   - **Gallery & History**: Reads from a local `sqlite3` database (`history.db`) to display, play, and provide download links for previously generated MP4s, WAVs, and JSON metadata.
2. **Parallel Pipeline (`main.py`)**: Uses `concurrent.futures.ThreadPoolExecutor` (capped at 4 workers to prevent API rate limits). It securely passes the `streamlit.runtime.scriptrunner.add_script_run_ctx` down to the threads so progress updates stream back to the UI in real-time.
3. **Audio Mixing (`src/utils.py`)**: Uses `pydub`. It applies automatic `0dBFS` normalization, fades, and crucially: when mixing synthesized vocals with the instrumental track, it **ducks the instrumental by -3dB and boosts the vocals by +2dB**. This creates headroom and prevents digital clipping, ensuring clear lyrics.
4. **AI Subtitles & Vocals (`src/content_generator.py` & `src/tts_generator.py`)**: OpenAI (GPT-4) generates estimated timestamps and lyrical lines. This is saved as a `.srt` file. `ElevenLabs` generates the raw vocal audio based on these lines, which are stitched together across a single timeline.
5. **Video Encoding (`src/video_uploader.py`)**: Uses `ffmpeg`. It can either loop a static image downloaded from DALL-E 3, or run a complex `showwaves` visualizer. It securely burns the `.srt` subtitles into the final video. If subtitle burning fails (e.g., font/special char issues), a `try/except` block catches the `ffmpeg` error and attempts to generate the video *without* subtitles to ensure the pipeline doesn't crash entirely.

## Database Schema (`src/db.py`)
A local `history.db` SQLite database is maintained.
- `history` Table: `id` (PK), `hymn_name` (TEXT), `style` (TEXT), `video_path` (TEXT), `audio_path` (TEXT), `metadata_path` (TEXT), `date_created` (TIMESTAMP).

## Agent Design Rules & Observations
- **Do not alter `max_workers=min(4, len(midi_files))`** in `main.py` without considering API rate limits (HTTP 429).
- **Do not alter `audio = audio - 3`** inside `utils.py` without considering digital clipping when layering heavy bass instrumentals with vocals.
- **Always update `VERSION.md` and `CHANGELOG.md`** when adding new features.
- **Run `python -m pytest hymn_remaker/tests/`** before submitting. Tests use `pytest-mock` to avoid burning real API credits during CI/CD.

## Next Steps for Incoming Model (Gemini/Claude/GPT)
Based on the `ROADMAP.md` and `IDEAS.md`, I highly recommend the incoming agent tackles the following:
1. **AWS S3 / Google Cloud Storage Integration:** Currently, files are saved to `hymn_remaker/output/`. If this container crashes, the files are lost. Hooking the pipeline up to upload to a cloud bucket, and updating the SQLite DB to track S3 URLs instead of local file paths, will make this production-ready.
2. **Dynamic AI Prompts:** Currently, the user selects a "Style" (e.g., Deep House). We should parse the MIDI's tempo/metadata and use an LLM to generate a highly specific, dynamic prompt for MusicGen based on the song's intrinsic qualities (e.g., "120BPM upbeat energetic house").
3. **Webhook Support:** Add a feature to post the final YouTube link to a Discord Webhook or Twitter API upon successful upload.

Godspeed. The party never stops.
