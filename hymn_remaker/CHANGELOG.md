# Changelog

All notable changes to this project will be documented in this file.

## [1.5.0] - 2024-05-22
### Added
- **System Dashboard Tab**: Added a third tab to the Streamlit UI called "⚙️ System Dashboard". It queries the OS to track versions of `ffmpeg`, `fluidsynth`, Python dependencies in `requirements.txt`, and displays a project directory map. This is incredibly useful for users deploying via Docker to ensure their system binaries are correctly hooked up.
- **Granular TTS Progress Logging**: Passed the UI `status_callback` deep into the ElevenLabs iterative loop inside `tts_generator.py`. Rather than stalling the UI progress bar, it now ticks up per lyric line (e.g., "Synthesizing Vocal Line 3/10: 'Amazing Grace'").

## [1.4.0] - 2024-05-22
### Added
- **Dynamic AI Prompts**: Introduced `midi_analyzer.py` utilizing the `mido` library to parse `.mid` files at the byte-level, extracting the BPM and Time Signature. This is fed into GPT-4 to generate highly specific, expert-level Replicate prompts dynamically based on the user's base style.
- **Prompt Transparency**: The final generated prompt is now logged inside the JSON metadata and rendered in the UI expanders for full transparency on what was sent to the audio models.

## [1.3.0] - 2024-05-22
### Added
- **AWS S3 Integration**: Integrated `boto3` via `s3_uploader.py` to seamlessly backup generated MP4s, WAVs, and metadata to S3-compatible cloud storage. Added Cloud expander to the UI to configure target buckets.
- **Webhook Notifications**: Added `WebhookNotifier` capable of pinging Discord/Slack URLs with a rich-embed payload when a song completes, including S3 download links, YouTube URLs, and style metadata.
- **Cloud History Database**: Updated the local SQLite database to persist `remote_video_url` and `remote_audio_url`. The UI's Gallery tab now defaults to providing these cloud backup links if the local files are cleared or deleted.

## [1.2.0] - 2024-05-22
### Added
- **Gallery & History Database**: Integrated a local SQLite database (`history.db`) to track all successful generations. Added a "Gallery & History" tab to the Streamlit UI to browse, play, and download past remixes natively without having to re-generate them.
- **Dynamic FFmpeg Visualizer**: Added the ability to bypass static DALL-E 3 image generation in favor of a fast, dynamic, moving `showwaves` audio visualizer overlaid on a black background, complete with subtitle support.
- **Strict Input Validation**: Implemented a byte-level MIDI file signature checker (`MThd`) in the Web UI to reject non-MIDI uploads instantly.
- **Configurable Model Hash**: Abstracted the Replicate `musicgen` model hash into the `.env` configuration (`REPLICATE_MODEL`), and exposed it in the Web UI's sidebar for advanced power-users to swap out on the fly.

## [1.1.0] - 2024-05-21
### Added
- **Streamlit Web UI**: Replaced CLI-only interactions with a beautiful, robust `app.py` Web UI featuring dropdowns, sliders, and live progress bars.
- **Parallel Processing**: Integrated `concurrent.futures.ThreadPoolExecutor` to process multiple MIDI files concurrently.
- **ElevenLabs TTS**: Added automatic vocal track generation that synthesizes singing/spoken word based on public domain hymn lyrics.
- **Advanced Audio Processing**: Integrated `pydub` to normalize varying audio volumes, fade tracks, and seamlessly mix instrumental remakes with synthesized vocals (ducking instrumentals by -3dB and boosting vocals by +2dB).
- **Auto-Subtitles**: Implemented LLM-driven lyric synchronization that outputs `.srt` files and burns them into final MP4s using `ffmpeg`.
- **Docker Support**: Added `Dockerfile` and `docker-compose.yml` to effortlessly bundle system dependencies (`fluidsynth`, `ffmpeg`) alongside Python dependencies.
- **Global Documentation**: Established `VERSION.md`, `CHANGELOG.md`, `ROADMAP.md`, `TODO.md`, `VISION.md`, `IDEAS.md`, `DEPLOY.md`, `MEMORY.md`, and `HANDOFF.md`.

## [1.0.0] - 2024-05-15
### Added
- Initial project creation.
- Core CLI pipeline (`midi2audio`, Replicate `musicgen-melody`, OpenAI metadata).
- FFmpeg static video generation.
- YouTube Data API upload integration.
