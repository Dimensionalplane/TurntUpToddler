# Changelog

All notable changes to this project will be documented in this file.
The format is based on Keep a Changelog.

## [1.8.0] - Current
### Added
- **MusicXML Parsing:** Integrated `music21` library to natively parse `.mxl` and `.xml` sheet music files. The pipeline now extracts title, composer, and lyrics metadata directly from the source file before converting it to MIDI for the audio engine, allowing it to augment or bypass ChatGPT generative steps.
- **Docker Production Optimization:** Created a multi-stage `Dockerfile` and a `docker-compose.yml`. The build stage compiles the native C++ `pybind11` audio engine, and the runtime stage creates a lightweight container with `ffmpeg` and `fluidsynth` pre-installed, offering out-of-the-box local deployment for the UI and Daemon modes.
- **Pybind11 Native Rendering:** The `MidiRenderer` class now successfully instantiates the native C++ `HymnPlayer` engine (via `hymn_player_ext.so`) to render audio chunks directly into NumPy arrays and export them using `soundfile`, bypassing `midi2audio` shell commands.
- **Centralized Application Settings:** Created `hymn_remaker/settings.py` to house all hardcoded fallback paths (SoundFonts, caching directories) and default UI/Pipeline configuration strings. Refactored `main.py`, `app.py`, and source modules to import from this single source of truth.
- **TTS Alignment Smoothing:** Overhauled the vocal ducking system in `src/utils.py` to calculate the duration of the Replicate instrumental and apply an FFmpeg `atempo` time-stretch to the ElevenLabs vocal track to ensure perfectly matched runtimes before mixing.
- **Streamlit Subtitle Styling:** Exposed FFmpeg subtitle customization options (Font Size, Primary Color, Outline Color, Background Box Color) directly into the Streamlit UI sidebar, piping those parameters down into the `ffmpeg` filter string in `video_uploader.py`.

### Changed
- Pinned all Python dependencies in `requirements.txt` to exact versions to prevent upstream breaking changes across AI agent sessions.
- Updated `ROADMAP.md` and `TODO.md` to reflect the completion of Phase 3 and outline Phase 4 features (OMR, Live DJ Mode, Multi-Voice Harmonization).

## [1.7.2] - Previous
### Added
- Native C++ Engine implementation (`HymnPlayer`) utilizing FluidSynth API for low-level audio rendering.
- Omni-Workspace Compliance (UNIVERSAL_LLM_INSTRUCTIONS.md, AGENTS.md, etc.).
