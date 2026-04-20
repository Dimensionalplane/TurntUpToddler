# Changelog

All notable changes to this project will be documented in this file.
The format is based on Keep a Changelog.

## [1.13.0] - Current
### Added
- **24/7 Live DJ Radio Stream**: Created the `RadioStreamer` module (`hymn_remaker/src/radio_streamer.py`). This class spawns a background thread that continuously grabs generated `.mp4` videos from the `output/` directory, randomly shuffles them, and streams them in real-time to a live RTMP endpoint (such as YouTube Live or Twitch) using FFmpeg `-re -f flv`.
- Added the `--stream-rtmp <URL>` flag to `main.py` allowing users to boot up a headless, completely autonomous 24/7 internet radio station daemon alongside the normal rendering pipeline.

## [1.12.0] - Previous
### Added
- **Audio-Reactive Visualizer**: Added support for an FFmpeg-powered dynamic waveform overlay during the video assembly phase (`video_uploader.py`). Users can now toggle `--visualizer` via the CLI or check the "Audio-Reactive Visualizer" box in the Streamlit UI to dynamically trace the audio waveform over the generated DALL-E 3 album art.
- The visualizer logic intelligently adapts its bounds (`scale` and `pad` ratios) depending on whether the user selected a Standard 16:9 or Vertical 9:16 output format.

## [1.11.0] - Previous
### Added
- **AI Stem Separation**: Integrated Facebook's `demucs` library (`src/stem_separator.py`) into the pipeline. After Replicate generates the Deep House instrumental, the system now autonomously isolates the `drums`, `bass`, `vocals`, and `other` (melody) tracks.
- **Smart Audio Ducking**: Rewrote `process_audio` in `src/utils.py` to utilize the new AI stems, ducking melodic tracks during singing but keeping the drum stem untouched.
