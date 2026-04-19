# Changelog

All notable changes to this project will be documented in this file.
The format is based on Keep a Changelog.

## [1.9.0] - Current
### Added
- **OMR (Optical Music Recognition) Support**: Integrated the `oemer` library (`src/omr_processor.py`) to fully support reading raw physical sheet music images (`.png`, `.jpg`) and PDFs (`.pdf`). The pipeline now autonomously converts dropped or uploaded images into MusicXML (`.mxl`) files, bridging the gap between physical paper and the digital generative pipeline.
- Streamlit UI file uploaders and Watchdog daemon logic were expanded to handle the new image and PDF extensions natively.

### Fixed
- **Critical Thread Safety Regression:** Resolved a severe multithreading bug where the single global instance of the native C++ `HymnPlayer` engine was being shared concurrently across multiple `ThreadPoolExecutor` workers. `midi_renderer.py` now instantiates the Pybind11 engine locally per-call, eliminating race conditions and corrupted audio interleaving.
- **Streamlit Interactive Mode Bug:** Fixed the interactive UI review loop where clicking "Start Processing" would drop the file queue from `session_state` due to Streamlit's top-down rerun model. The pipeline now correctly tracks `completed_files` in session state to seamlessly resume execution after manual lyric/metadata edits are approved.
- Unpinned dependencies in `requirements.txt` to resolve a bug where python environment specific versions (e.g., `streamlit==1.56.0` or `Pillow==12.2.0`) caused cross-platform build failures.

## [1.8.0] - Previous
### Added
- **MusicXML Parsing:** Integrated `music21` library to natively parse `.mxl` and `.xml` sheet music files.
- **Docker Production Optimization:** Created a multi-stage `Dockerfile` and a `docker-compose.yml`.
- **Pybind11 Native Rendering:** The `MidiRenderer` class now successfully instantiates the native C++ `HymnPlayer` engine.
- **Centralized Application Settings:** Created `hymn_remaker/settings.py`.
- **TTS Alignment Smoothing:** Overhauled the vocal ducking system in `src/utils.py` using FFmpeg `atempo`.
- **Streamlit Subtitle Styling:** Exposed FFmpeg subtitle customization options.
