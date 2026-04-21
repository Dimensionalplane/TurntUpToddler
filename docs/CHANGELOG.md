# Changelog

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
