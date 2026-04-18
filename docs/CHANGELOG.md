# Changelog

All notable changes to this project will be documented in this file.
The format is based on Keep a Changelog.

## [1.7.2] - Current
### Added
- **Native C++ Engine:** Implemented the `HymnPlayer` class (`src/engine/HymnPlayer.cpp`) utilizing the FluidSynth API for low-level audio rendering.
- **C++ Build System:** Added a standard `Makefile` to compile the native C++ code and test suite.
- **Native Testing:** Added `tests/HymnPlayerTests.cpp` featuring dynamic MIDI file creation for robust unit testing of the native engine.
- **Omni-Workspace Compliance:** Massive documentation overhaul to comply with cross-repository LLM agent standards. Created `docs/UNIVERSAL_LLM_INSTRUCTIONS.md` and updated `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `GPT.md`, and `copilot-instructions.md`.
- **Project Documentation Expansion:** Extensively detailed `VISION.md`, `ROADMAP.md`, `MEMORY.md`, and `DEPLOY.md` to capture current architectural decisions and future feature goals.

### Fixed
- **FluidSynth Clock Synchronization:** Corrected an issue in `HymnPlayer::renderAudio` where calling both `fluid_synth_process` and `fluid_synth_write_float` caused double-advancement of the synth clock resulting in audio skipping.

## [1.7.1] - Previous
### Added
- **Daemon Mode:** Implemented `--daemon` CLI flag using the `watchdog` library to continuously monitor the input directory for automated processing.
- **Vertical Video & Shorts Extraction:** Added logic in `video_uploader.py` to support 9:16 vertical formatting. Added `--create-shorts` flag utilizing FFmpeg's `segment` muxer to generate 15-second clips.
- **Cost Optimization:** Implemented local DALL-E image caching in `.cache/art/` using MD5 hashing of prompts to prevent redundant API charges.
- **Robust Subtitles:** Added a retry loop to FFmpeg subtitle burning that strips non-ASCII characters upon crash, falling back to a textless video if all retries fail.
- **Parameter Exposure:** Exposed ElevenLabs `voice_id` and `model` configuration to the CLI and Streamlit UI.

### Fixed
- **UnboundLocalError:** Fixed a crash during pipeline failure cleanup in `main.py` by properly initializing path variables to `None` at the start of scope.
