# Changelog

All notable changes to this project will be documented in this file.
The format is based on Keep a Changelog.

## [1.10.0] - Current
### Added
- **Multi-Voice Harmonization**: Upgraded the ElevenLabs TTS integration (`tts_generator.py`) to parse multiple, comma-separated Voice IDs. The pipeline now generates separate vocal tracks for each voice, pitch-shifts secondary voices (e.g., +4 and +7 semitones via `pydub`) to create lush harmonies, pans them stereo-spatially, and overlays them onto the master vocal track.
- **Dynamic Tempo Matching**: Updated `midi_renderer.py` to extract exact BPM and Tempo data directly from the input MIDI/MXL file using `mido`. This precise integer is dynamically injected into the Replicate/MusicGen Deep House prompt to strictly enforce original tempo integrity in the final audio artifact.
- **Hymn Editor UI Toolbar**: Rebuilt `app.py` into a multi-tab Streamlit dashboard. Added an extensive "Hymn Editor" tab that exposes backend rendering tools. Users can upload individual MIDI/MXL files, preview native C++ audio renders immediately, parse sheet music metadata, and edit/export `.txt` lyrics without waiting for the full pipeline batch queue to finish.

### Fixed
- **Critical Thread Safety Regression:** Resolved a severe multithreading bug where the single global instance of the native C++ `HymnPlayer` engine was being shared concurrently across multiple `ThreadPoolExecutor` workers. `midi_renderer.py` now instantiates the Pybind11 engine locally per-call.
- **Streamlit Interactive Mode Bug:** Fixed the interactive UI review loop where clicking "Start Processing" would drop the file queue from `session_state`.
- **Streamlit Infinite Deadlock**: Removed a duplicate, orphaned `ThreadPoolExecutor` loop that was causing `interactive_mode` to hang indefinitely.

## [1.9.0] - Previous
### Added
- **OMR (Optical Music Recognition) Support**: Integrated the `oemer` library (`src/omr_processor.py`) to fully support reading raw physical sheet music images (`.png`, `.jpg`) and PDFs (`.pdf`).
- Streamlit UI file uploaders and Watchdog daemon logic were expanded to handle the new image and PDF extensions natively.

### Fixed
- Repinned the `streamlit` package version in `requirements.txt` from a hallucinated future version (`1.56.0`) back to the correct stable runtime version to restore Docker build functionality.
