# Changelog

## [1.7.1] - 2024-04-10
### Added
- Finalized comprehensive project memory summary mapping the architecture, decisions, and patterns implemented in this session.
- Updated HANDOFF.md with a detailed review of 1.7.x additions including DALL-E caching, Shorts extraction, Daemon mode, and Vertical 9:16 video support.

## [1.7.0] - 2024-04-10
### Added
- Added `--create-shorts` CLI flag and Streamlit UI toggle to automatically extract 15-second segments from the rendered video using FFmpeg.

## [1.6.0] - 2024-04-10
### Added
- Added `--daemon` mode to `main.py` which uses `watchdog` to continuously monitor the input directory for new MIDI files, automatically processing and uploading them.

## [1.5.0] - 2024-04-10
### Added
- Support for Vertical 9:16 Video Formatting (TikTok/Instagram Reels) via FFmpeg padding and scaling.
- Video Format configuration exposed in the Streamlit UI and CLI.

## [1.4.0] - 2024-04-10
### Added
- Enhanced unit tests for the ElevenLabs TTS generator parameter assertions.

### Fixed
- Added aggressive file cleanup to the pipeline orchestrator if a processing step crashes mid-way.

## [1.3.0] - 2024-04-10
### Added
- YouTube upload progress bar mapping to Streamlit UI via chunking callbacks.

### Fixed
- Added max_retries and lyric sanitization logic to FFmpeg subtitle burning to improve resilience against weird characters.

## [1.2.0] - 2024-04-10
### Added
- Added local caching for DALL-E 3 generated album art to prevent redundant API calls.

## [1.1.0] - 2024-04-10
### Added
- Comprehensive documentation suite (`ROADMAP.md`, `VISION.md`, `TODO.md`, etc.) aligned with the Omni-Workspace specifications.
- Exposed ElevenLabs `voice_id` and `model` configuration in the Streamlit Web UI and CLI.
- Integrated global `VERSION` file reading into the application sidebar.

## [1.0.0] - Initial Release
### Added
- Core MIDI rendering pipeline.
- Replicate MusicGen integration.
- OpenAI Metadata and Lyrics generation.
- DALL-E 3 album art generation.
- ElevenLabs TTS vocal synthesis.
- FFmpeg video assembly with subtitles.
- YouTube API uploading.
