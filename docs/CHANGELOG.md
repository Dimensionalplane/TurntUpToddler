# Changelog

All notable changes to this project will be documented in this file.
The format is based on Keep a Changelog.

## [1.14.0] - Current
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
