# Changelog

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
All notable changes to this project will be documented in this file.
The format is based on Keep a Changelog.

## [1.17.0] - Current
### Added
- **Expanded Audio-Reactive Visualizers**: Dramatically expanded the capabilities of the FFmpeg video generation block. The pipeline now supports multiple types of audio-reactive waveform overlays: `cline`, `line`, `p2p` (via FFmpeg's `showwaves` filter), and beautiful Lissajous curves (via `avectorscope`).
- The Streamlit UI sidebar now dynamically exposes a visualizer mode selection dropdown when the "Audio-Reactive Visualizer" checkbox is toggled.
- Added comprehensive unit tests in `test_video_uploader.py` to assert the correct construction of complex FFmpeg visualizer filter strings.

## [1.16.0] - Previous
### Added
- **Interactive Radio UI**: Completed Phase 6 roadmap priority by integrating the `RadioStreamer` directly into the Streamlit Web UI. Users can now enter their RTMP/Icecast URL, start a background 24/7 radio broadcast daemon thread directly from the browser, view the currently streaming `.mp4` track, and utilize thread-safe `Event` hooks to "Skip Track" or "Stop Broadcast" manually without touching the CLI.
- Added comprehensive unit tests in `test_radio_streamer.py` to validate `skip_track` and `stop` thread termination logic.

## [1.15.0] - Previous
### Changed
- **Documentation Suite Finalization**: Massively overhauled the core documentation structure (`ROADMAP.md`, `VISION.md`, `TODO.md`, `HANDOFF.md`) to reflect the completed state of the Omni-Workspace pipeline. All Phase 1 through Phase 5 features are now marked as `[x]`.

## [1.14.0] - Previous
### Added
- **Advanced Subtitle Parsing**: Rewrote the logic in `hymn_remaker/src/musicxml_parser.py` using `music21`. Instead of aggressively stripping hyphens and extracting a flat string for OpenAI to consume, the parser now reads the internal `metronomeMarkBoundaries` and raw note `offsets`. It calculates absolute timestamps (in seconds) for every note and groups syllables (`begin`, `middle`, `end`) together. This returns a structured list of exact start/end dictionary timings.