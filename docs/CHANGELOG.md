# Changelog

All notable changes to this project will be documented in this file.
The format is based on Keep a Changelog.

## [1.15.0] - Current
### Changed
- **Documentation Suite Finalization**: Massively overhauled the core documentation structure (`ROADMAP.md`, `VISION.md`, `TODO.md`, `HANDOFF.md`) to reflect the completed state of the Omni-Workspace pipeline. The project has successfully grown from a basic Python wrapper to an advanced, multi-language, multi-AI containerized broadcasting station capable of translating physical sheet music into an automated, live-streaming 24/7 Deep House YouTube channel. All Phase 1 through Phase 5 features are now marked as `[x]` (completed) and the initial roadmap is fully mapped into actionable deployment instructions.

## [1.14.0] - Previous
### Added
- **Advanced Subtitle Parsing**: Rewrote the logic in `hymn_remaker/src/musicxml_parser.py` using `music21`. Instead of aggressively stripping hyphens and extracting a flat string for OpenAI to consume, the parser now reads the internal `metronomeMarkBoundaries` and raw note `offsets`. It calculates absolute timestamps (in seconds) for every note and groups syllables (`begin`, `middle`, `end`) together. This returns a structured list of exact start/end dictionary timings.
- **Pipeline Integration**: `main.py` and `app.py` were updated to recognize the new structured exact lyric arrays. If accurate `.mxl` timing data is present, the pipeline now completely skips the GPT prompt to generate/guess lyrics and passes the native sheet music timings directly to the TTS generator and FFmpeg subtitle burner, drastically improving audio-visual sync precision.
- **UI Expansion**: The "Hymn Editor" tab in `app.py` now displays the internally parsed JSON list of subtitle exact timings alongside the flat lyric text for debugging and editing.

## [1.13.0] - Previous
### Added
- **24/7 Live DJ Radio Stream**: Created the `RadioStreamer` module to push generated `.mp4` chunks to RTMP live streaming endpoints using FFmpeg.
- **Audio-Reactive Visualizer**: Added support for an FFmpeg-powered dynamic waveform overlay during the video assembly phase (`video_uploader.py`).

## [1.12.0] - Previous
### Added
- **Audio-Reactive Visualizer**: Added support for an FFmpeg-powered dynamic waveform overlay during the video assembly phase (`video_uploader.py`). Users can now toggle `--visualizer` via the CLI or Streamlit UI.

## [1.11.0] - Previous
### Added
- **AI Stem Separation**: Integrated Facebook's `demucs` library into the pipeline to autonomously isolate `drums`, `bass`, `vocals`, and `other` tracks from the Replicate output.
- **Smart Audio Ducking**: Re-engineered `process_audio` to strictly duck melodic/bass stems during TTS vocal playback, preserving the full punch of the house drum loop.

### Fixed
- Re-architected `app.py` to fix Streamlit `session_state` resets, adding a dedicated "Hymn Editor" tab to prevent execution blocks from overlapping.
- Corrected the `fluid_settings` timer instantiation in the native C++ `HymnPlayer` engine to use the "sample" timer instead of the real-time system clock, unlocking the ability to render offline buffers substantially faster than real-time without skipping frames.
