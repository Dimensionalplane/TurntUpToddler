# Changelog

All notable changes to this project will be documented in this file.
The format is based on Keep a Changelog.

## [1.16.0] - Current
### Added
- **Interactive Radio UI**: Completed Phase 6 roadmap priority by integrating the `RadioStreamer` directly into the Streamlit Web UI. Users can now enter their RTMP/Icecast URL, start a background 24/7 radio broadcast daemon thread directly from the browser, view the currently streaming `.mp4` track, and utilize thread-safe `Event` hooks to "Skip Track" or "Stop Broadcast" manually without touching the CLI.
- Added comprehensive unit tests in `test_radio_streamer.py` to validate `skip_track` and `stop` thread termination logic.

## [1.15.0] - Previous
### Changed
- **Documentation Suite Finalization**: Massively overhauled the core documentation structure (`ROADMAP.md`, `VISION.md`, `TODO.md`, `HANDOFF.md`) to reflect the completed state of the Omni-Workspace pipeline. All Phase 1 through Phase 5 features are now marked as `[x]`.

## [1.14.0] - Previous
### Added
- **Advanced Subtitle Parsing**: Rewrote the logic in `hymn_remaker/src/musicxml_parser.py` using `music21`. Instead of aggressively stripping hyphens and extracting a flat string for OpenAI to consume, the parser now reads the internal `metronomeMarkBoundaries` and raw note `offsets`. It calculates absolute timestamps (in seconds) for every note and groups syllables (`begin`, `middle`, `end`) together. This returns a structured list of exact start/end dictionary timings.
- **Pipeline Integration**: `main.py` and `app.py` were updated to recognize the new structured exact lyric arrays. If accurate `.mxl` timing data is present, the pipeline now completely skips the GPT prompt to generate/guess lyrics and passes the native sheet music timings directly to the TTS generator and FFmpeg subtitle burner, drastically improving audio-visual sync precision.
- **UI Expansion**: The "Hymn Editor" tab in `app.py` now displays the internally parsed JSON list of subtitle exact timings alongside the flat lyric text for debugging and editing.

## [1.13.0] - Previous
### Added
- **24/7 Live DJ Radio Stream**: Created the `RadioStreamer` module to push generated `.mp4` chunks to RTMP live streaming endpoints using FFmpeg.
- **Audio-Reactive Visualizer**: Added support for an FFmpeg-powered dynamic waveform overlay during the video assembly phase (`video_uploader.py`).
